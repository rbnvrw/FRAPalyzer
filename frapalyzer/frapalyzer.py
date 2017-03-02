import numpy as np
from nd2reader import ND2Reader

from frapalyzer.errors import InvalidROIError
from scipy.optimize import least_squares


class FRAPalyzer(object):
    """
    Analyze Nikon ND2 stimulation FRAP experiments automatically
    """

    def __init__(self, nd2_filename):
        self._file = ND2Reader(nd2_filename)
        self._micron_per_pixel = self._file.metadata["pixel_microns"]
        self.background_roi = self._get_roi('background')
        self.reference_roi = self._get_roi('reference')
        self.stimulation_roi = self._get_roi('stimulation')
        self.bleach_time_index = self._get_bleach_time_index()
        self.timesteps = self._get_timesteps()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def close(self):
        if self._file:
            self._file.close()

    def _get_roi(self, roi_type='background'):
        """
        Get the background ROI
        :return:
        """
        if 'rois' not in self._file.metadata:
            return None

        for roi in self._file.metadata['rois']:
            if roi['type'] == roi_type:
                return roi

        return None

    @property
    def metadata(self):
        return self._file.metadata

    def get_normalized_stimulation(self):
        """
        Get the normalized and reference corrected stimulation signal
        :return:
        """
        reference = self.get_mean_intensity(self.reference_roi, keep_time=True)
        stimulated = self.get_mean_intensity(self.stimulation_roi, keep_time=True)

        # before this index: pre-bleach scan, after: post-bleach
        bleach_time_index = self.bleach_time_index

        ref_pre_bleach = reference[:bleach_time_index]
        stim_pre_bleach = stimulated[:bleach_time_index]

        # normalize both with the pre-bleach scans
        ref_norm = np.divide(reference, np.mean(ref_pre_bleach))
        stim_norm = np.divide(stimulated, np.mean(stim_pre_bleach))

        # correct stimulated signal for acquisition bleaching using the reference
        corrected = np.divide(stim_norm, ref_norm)

        return corrected

    def fit_exponential_recovery(self):
        """
        Fit an exponential recovery function
        :return:
        """
        data = self.get_normalized_stimulation()
        bleach_time = self.bleach_time_index
        timesteps = self.timesteps

        # Everything after bleach
        recovery_data = data[bleach_time:]

        # Guess for recovery and half time
        recovery = np.max(recovery_data)
        half_time_index = np.argmin(np.abs(recovery_data - recovery / 2.0))
        try:
            half_time = timesteps[half_time_index]
        except IndexError:
            half_time = timesteps[bleach_time]

        # Make least squares fit
        def frap_fit_function(params, t, y):
            ln_half = np.log(0.5)
            return params[0] * (1 - np.exp(ln_half / params[1] * t)) - y

        res_lsq = least_squares(frap_fit_function, (recovery, half_time), args=(timesteps[bleach_time:], recovery_data))

        if res_lsq.success:
            recovery = res_lsq.x[0]
            half_time = res_lsq.x[1]

        return recovery, half_time

    def _get_bleach_time_index(self):
        """
        Get the time index after which bleaching was performed
        :return:
        """
        current_index = 0
        for loop in self._file.metadata['experiment']['loops']:
            if loop['stimulation']:
                return int(np.round(current_index))

            current_index += loop['duration'] / loop['sampling_interval']

        return int(np.round(current_index))

    def _get_timesteps(self):
        """
        Get the time index after which bleaching was performed
        :return:
        """
        timesteps = np.array([])
        current_time = 0.0
        for loop in self._file.metadata['experiment']['loops']:
            if loop['stimulation']:
                continue

            timesteps = np.concatenate(
                (timesteps, np.arange(current_time, current_time + loop['duration'], loop['sampling_interval'])))
            current_time += loop['duration']

        # if experiment did not finish, number of timesteps is wrong. Take correct amount of leading timesteps.
        return timesteps[:self._file.metadata['num_frames']]

    @staticmethod
    def _check_roi(roi):
        """
        Checks if this is a valid ROI
        :param roi:
        :return:
        """
        if roi is None or 'shape' not in roi:
            raise InvalidROIError('Invalid ROI specified')

    def get_mean_intensity(self, roi, keep_time=False, subtract_background=True, only_gt_zero=True):
        """
        Calculate the mean background intensity
        :return:
        """
        self._check_roi(roi)

        image = self._get_slice_from_roi(roi)

        if subtract_background:
            background = self.get_mean_intensity(self.background_roi, keep_time=False, subtract_background=False,
                                                 only_gt_zero=True)
            image = np.subtract(image, background)

        if only_gt_zero:
            image[np.isnan(image)] = -1
            image[image <= 0] = np.nan

        if keep_time:
            return np.nanmean(np.nanmean(image, axis=2), axis=1)
        else:
            return np.nanmean(image)

    def _to_pixel(self, micron):
        return np.round(np.divide(micron, self._micron_per_pixel)).astype(np.int)

    def _get_slice_from_roi(self, roi):
        """
        Get the part of the image that is this ROI
        :param roi:
        :return:
        """
        if roi['shape'] == 'circle':
            image = self._get_circular_slice_from_roi(roi)
        elif roi['shape'] == 'rectangle':
            image = self._get_rectangular_slice_from_roi(roi)
        else:
            raise InvalidROIError('Only circular and rectangular ROIs are supported')
        return image

    def _get_circular_slice_from_roi(self, roi):
        """
        Get mean intensity of a circular ROI
        :param roi:
        :return:
        """
        center = self._to_pixel(roi["positions"][0])
        radius = self._to_pixel(roi["sizes"][0, 0])
        coordinates = np.round(np.add(np.repeat(center[0:2], 2), np.multiply(radius, np.tile([-1, 1], (2,)))))
        rect = self._get_rect_from_images(coordinates.astype(np.int))

        # Put NaNs on places that are not inside the circle
        x, y = np.meshgrid(*map(np.arange, rect.shape[1:]), indexing='ij')
        mask = ((x - radius) ** 2 + (y - radius) ** 2) > radius ** 2
        rect[:, mask] = np.nan

        return rect

    def _get_rectangular_slice_from_roi(self, roi):
        """
        Return a rectangular slice of the ROI
        :param roi:
        :return:
        """
        coordinates = np.round(np.add(np.repeat(roi['positions'][0, 0:2], 2),
                                      np.multiply(np.repeat(roi["sizes"][0, 0:2], 2), np.tile([-0.5, 0.5], (2,)))))
        return self._get_rect_from_images(coordinates.astype(np.int))

    def _get_rect_from_images(self, rect):
        """
        Rect: (left, right, bottom, top)
        :param rect:
        :return:
        """
        images = []

        for t in range(self._file.sizes['t']):
            image = self._file[int(t)][rect[2]:rect[3], rect[0]:rect[1]]
            images.append(image)

        return np.array(images, dtype=self._file.pixel_type)

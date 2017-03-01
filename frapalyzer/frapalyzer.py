import numpy as np
from nd2reader import ND2Reader

from frapalyzer.errors import InvalidROIError


class FRAPalyzer(object):
    """
    Analyze Nikon ND2 stimulation FRAP experiments automatically
    """

    def __init__(self, nd2_filename):
        self._file = ND2Reader(nd2_filename)
        self._micron_per_pixel = self._file.metadata["pixel_microns"]
        self._background_roi = self._get_roi('background')
        self._reference_roi = self._get_roi('reference')
        self._stimulation_roi = self._get_roi('stimulation')
        self._bleach_time_index = None
        self._timesteps = None

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

    @property
    def background_roi(self):
        if not hasattr(self, '_background_roi'):
            self._background_roi = self._get_roi('background')
        return self._background_roi

    @property
    def reference_roi(self):
        if not hasattr(self, '_reference_roi'):
            self._reference_roi = self._get_roi('reference')
        return self._reference_roi

    @property
    def stimulation_roi(self):
        if not hasattr(self, '_stimulation_roi'):
            self._stimulation_roi = self._get_roi('stimulation')
        return self._stimulation_roi

    @property
    def bleach_time_index(self):
        if self._bleach_time_index is not None:
            return self._bleach_time_index
        self._bleach_time_index = self._get_bleach_time_index()
        return self._bleach_time_index

    @property
    def timesteps(self):
        if self._timesteps is not None:
            return self._timesteps
        self._timesteps = self._get_timesteps()
        return self._timesteps

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

    def get_mean_intensity(self, roi, keep_time=False, subtract_background=True, only_gt_zero=True):
        """
        Calculate the mean background intensity
        :return:
        """
        if roi is None or 'shape' not in roi:
            raise InvalidROIError('Invalid ROI specified')

        if roi['shape'] == 'circle':
            image = self._get_circular_slice_from_roi(roi)
        elif roi['shape'] == 'rectangle':
            image = self._get_rectangular_slice_from_roi(roi)
        else:
            raise InvalidROIError('Only circular and rectangular ROIs are supported')

        if subtract_background:
            background = self.get_mean_intensity(self.background_roi, keep_time=False, subtract_background=False,
                                                 only_gt_zero=True)
            image = np.subtract(image, background)

        if only_gt_zero:
            image[np.isnan(image)] = -1
            image[image <= 0] = np.nan

        if keep_time:
            return np.nanmean(np.nanmean(image, axis=2), axis=1).compressed()
        else:
            return np.nanmean(image)

    def _to_pixel(self, micron):
        return np.round(np.divide(micron, self._micron_per_pixel)).astype(np.int)

    def _get_circular_slice_from_roi(self, roi):
        """
        Get mean intensity of a circular ROI
        :param roi:
        :return:
        """
        center = self._to_pixel(roi["positions"][0])
        radius = self._to_pixel(roi["sizes"][0, 0])

        rect = self._get_rect_from_images(
            (center[0] - radius, center[0] + radius, center[1] - radius, center[1] + radius))

        # Put NaNs on places that are not inside the circle
        x, y = np.meshgrid(*map(np.arange, rect.shape[1:]), indexing='ij')
        mask = ((x - radius) ** 2 + (y - radius) ** 2) > radius ** 2
        rect[:, mask] = np.nan

        return rect

    def _get_rectangular_slice_from_roi(self, roi):
        """
        Coordinates are the center coordinates of the ROI
        :param roi:
        :return:
        """
        left = self._to_pixel(roi["positions"][0, 0] - roi["sizes"][0, 0] / 2)
        right = self._to_pixel(roi["positions"][0, 0] + roi["sizes"][0, 0] / 2)
        top = self._to_pixel(roi["positions"][0, 1] + roi["sizes"][0, 1] / 2)
        bottom = self._to_pixel(roi["positions"][0, 1] - roi["sizes"][0, 1] / 2)

        return self._get_rect_from_images((left, right, bottom, top))

    def _get_rect_from_images(self, rect):
        """
        Rect: (left, right, bottom, top)
        :param rect:
        :return:
        """
        images = []

        for t in range(self._file.sizes['t']):
            image = self._file[t][rect[2]:rect[3], rect[0]:rect[1]]
            images.append(image)

        return np.array(images, dtype=self._file.pixel_type)

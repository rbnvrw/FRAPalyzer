import numpy as np
from nd2reader import ND2Reader


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

    def get_normalized_stimulation(self):
        """
        Get the normalized and reference corrected stimulation signal
        :return:
        """
        reference = self.get_mean_intensity(self.reference_roi, keep_time=True)
        stimulated = self.get_mean_intensity(self.stimulation_roi, keep_time=True)

        # before this index: pre-bleach scan, after: post-bleach
        bleach_time_index = self._get_bleach_time_index()

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

    def get_mean_intensity(self, roi, keep_time=False, subtract_background=True, only_gt_zero=True):
        """
        Calculate the mean background intensity
        :return:
        """

        if roi['shape'] == 'circle':
            image = self._get_circular_slice_from_roi(roi)
        elif roi['shape'] == 'rectangle':
            image = self._get_rectangular_slice_from_roi(roi)
        else:
            raise ValueError('Only circular and rectangular ROIs are supported')

        if subtract_background:
            background = self.get_mean_intensity(self.background_roi, keep_time=False, subtract_background=False,
                                                 only_gt_zero=True)
            image = np.subtract(image, background)

        if only_gt_zero:
            image = np.ma.masked_less_equal(image, 0)

        if keep_time:
            return image.mean(axis=2).mean(axis=1).compressed()
        else:
            return image.mean()

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

        images = []
        for t in range(self._file.sizes['t']):
            image = self._file[t]
            x, y = np.ogrid[-center[1]:self._file.metadata["height"] - center[1], -center[0]:
                            self._file.metadata["width"] - center[0]]
            mask = x ** 2 + y ** 2 > radius ** 2
            images.append(np.ma.masked_where(mask, image))

        return np.ma.array(images, dtype=self._file.pixel_type)

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

        images = []
        for t in range(self._file.sizes['t']):
            image = self._file[t]
            x, y = np.ogrid[0:self._file.metadata["height"], 0:self._file.metadata["width"]]
            mask = np.bitwise_or(x > right, np.bitwise_or(x < left, np.bitwise_or(y > top, y < bottom)))
            images.append(np.ma.masked_where(mask, image))

        return np.ma.array(images, dtype=self._file.pixel_type)
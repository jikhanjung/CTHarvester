"""Property-based tests for the image pipeline and ROI arithmetic.

These replace a template whose single test body was
``pytest.skip("Template - to be implemented in Phase 4")``.

What a property test is worth here: the functions below are all small, pure and
total over a large input space, which is exactly where example-based tests keep
missing a corner. The overflow property in TestAverageImagesProperties is the
clearest case -- ``average_images`` widens the dtype before adding precisely so
that two bright uint8 pixels do not wrap, and no fixed example pins that down
unless someone thinks to pick 200 and 200.

The hypothesis profile (derandomized, 100 examples) is registered in
tests/conftest.py.
"""

import numpy as np
import pytest
from hypothesis import assume, given
from hypothesis import strategies as st
from hypothesis.extra import numpy as hnp

from ui.widgets.roi_manager import ROIManager
from utils.image_utils import average_images, downsample_image

# The two depths the application actually handles; load_image_as_array and the
# thumbnail pipeline are built around this pair.
IMAGE_DTYPES = (np.uint8, np.uint16)


def gray_images(dtype, min_side=1, max_side=64):
    """Grayscale arrays of the given dtype, in the shapes the pipeline sees."""
    return hnp.arrays(
        dtype=dtype,
        shape=hnp.array_shapes(min_dims=2, max_dims=2, min_side=min_side, max_side=max_side),
        elements=st.integers(min_value=0, max_value=int(np.iinfo(dtype).max)),
    )


@pytest.mark.property
class TestDownsampleProperties:
    """Properties of utils.image_utils.downsample_image."""

    @given(
        img=gray_images(np.uint8),
        factor=st.integers(min_value=1, max_value=8),
        method=st.sampled_from(["subsample", "average"]),
    )
    def test_dtype_is_preserved(self, img, factor, method):
        """Downsampling never changes the bit depth.

        This is the property the thumbnail pyramid depends on: level N+1 is
        built from level N, so a dtype that drifts once drifts on every
        subsequent level. `average` computes a float mean internally and casts
        back, which is where it could be lost.
        """
        assume(min(img.shape) >= factor)
        assert downsample_image(img, factor=factor, method=method).dtype == img.dtype

    @given(img=gray_images(np.uint8), factor=st.integers(min_value=1, max_value=8))
    def test_subsample_shape_is_ceiling_division(self, img, factor):
        """Strided slicing keeps the partial trailing row/column."""
        h, w = img.shape
        out = downsample_image(img, factor=factor, method="subsample")
        assert out.shape == (-(-h // factor), -(-w // factor))

    @given(img=gray_images(np.uint8), factor=st.integers(min_value=1, max_value=8))
    def test_average_shape_is_floor_division(self, img, factor):
        """Block averaging drops the remainder instead, which is the whole
        reason the two methods do not agree on output size."""
        assume(min(img.shape) >= factor)
        h, w = img.shape
        out = downsample_image(img, factor=factor, method="average")
        assert out.shape == (h // factor, w // factor)

    @given(
        img=gray_images(np.uint8),
        factor=st.integers(min_value=1, max_value=8),
    )
    def test_average_stays_within_input_range(self, img, factor):
        """A mean cannot leave the range of the values it averaged.

        Violating this means the block sum wrapped -- the same overflow class
        as average_images, reached by a different route.
        """
        assume(min(img.shape) >= factor)
        out = downsample_image(img, factor=factor, method="average")
        assume(out.size > 0)
        assert out.min() >= img.min()
        assert out.max() <= img.max()

    @given(img=gray_images(np.uint8))
    def test_factor_one_subsample_is_identity(self, img):
        assert np.array_equal(downsample_image(img, factor=1, method="subsample"), img)

    @given(img=gray_images(np.uint8), method=st.text(min_size=1, max_size=8))
    def test_unknown_method_raises(self, img, method):
        assume(method not in ("subsample", "average"))
        with pytest.raises(ValueError):
            downsample_image(img, factor=2, method=method)


@pytest.mark.property
class TestAverageImagesProperties:
    """Properties of utils.image_utils.average_images."""

    @given(dtype=st.sampled_from(IMAGE_DTYPES), data=st.data())
    def test_never_overflows(self, dtype, data):
        """Every output pixel lies between the two inputs it came from.

        This is the property the function exists for. Adding two uint8 arrays
        without widening wraps for any pair summing over 255, so a naive
        implementation fails this on the majority of bright inputs -- while
        still passing any test written around dim example images.
        """
        img1 = data.draw(gray_images(dtype))
        img2 = data.draw(
            hnp.arrays(
                dtype=dtype,
                shape=img1.shape,
                elements=st.integers(min_value=0, max_value=int(np.iinfo(dtype).max)),
            )
        )

        result = average_images(img1, img2)

        assert np.all(result >= np.minimum(img1, img2))
        assert np.all(result <= np.maximum(img1, img2))

    @given(dtype=st.sampled_from(IMAGE_DTYPES), data=st.data())
    def test_is_commutative(self, dtype, data):
        """Averaging two slices does not depend on which was read first."""
        img1 = data.draw(gray_images(dtype))
        img2 = data.draw(
            hnp.arrays(
                dtype=dtype,
                shape=img1.shape,
                elements=st.integers(min_value=0, max_value=int(np.iinfo(dtype).max)),
            )
        )
        assert np.array_equal(average_images(img1, img2), average_images(img2, img1))

    @given(dtype=st.sampled_from(IMAGE_DTYPES), data=st.data())
    def test_averaging_a_slice_with_itself_is_the_slice(self, dtype, data):
        """(x + x) // 2 == x exactly, for every x, once the widening is right.

        A duplicated slice is a real input: an odd-length stack pairs the last
        image with itself.
        """
        img = data.draw(gray_images(dtype))
        result = average_images(img, img)
        assert result.dtype == img.dtype
        assert np.array_equal(result, img)


@pytest.mark.property
class TestROIBoundsProperties:
    """Properties of ui.widgets.roi_manager.ROIManager coordinate handling."""

    coord = st.integers(min_value=0, max_value=10_000)

    @given(x1=coord, y1=coord, x2=coord, y2=coord)
    def test_bounds_are_normalised_whatever_the_drag_direction(self, x1, y1, x2, y2):
        """A box dragged up-and-left must come back the same as down-and-right.

        The widget hands over raw mouse-down/mouse-up coordinates, so both
        orderings arrive in practice.
        """
        roi = ROIManager()
        roi.set_roi_bounds(x1, y1, x2, y2)
        left, top, right, bottom = roi.get_roi_bounds()

        assert left <= right
        assert top <= bottom
        assert {left, right} == {min(x1, x2), max(x1, x2)}
        assert {top, bottom} == {min(y1, y2), max(y1, y2)}

    @given(x1=coord, y1=coord, x2=coord, y2=coord)
    def test_dimensions_agree_with_bounds(self, x1, y1, x2, y2):
        """get_roi_dimensions is not allowed to disagree with get_roi_bounds."""
        roi = ROIManager()
        roi.set_roi_bounds(x1, y1, x2, y2)
        left, top, right, bottom = roi.get_roi_bounds()
        width, height = roi.get_roi_dimensions()

        assert (width, height) == (right - left, bottom - top)
        assert width >= 0
        assert height >= 0

    @given(x1=coord, y1=coord, x2=coord, y2=coord)
    def test_corners_are_inside_their_own_roi(self, x1, y1, x2, y2):
        """contains_point is inclusive of the bounds it was given."""
        roi = ROIManager()
        roi.set_roi_bounds(x1, y1, x2, y2)
        left, top, right, bottom = roi.get_roi_bounds()

        assert roi.contains_point(left, top)
        assert roi.contains_point(right, bottom)

    @given(x1=coord, y1=coord, x2=coord, y2=coord, dx=st.integers(1, 100))
    def test_points_beyond_the_edge_are_outside(self, x1, y1, x2, y2, dx):
        roi = ROIManager()
        roi.set_roi_bounds(x1, y1, x2, y2)
        left, top, right, bottom = roi.get_roi_bounds()

        assert not roi.contains_point(right + dx, top)
        assert not roi.contains_point(left, bottom + dx)

    @given(
        x1=coord,
        y1=coord,
        x2=coord,
        y2=coord,
    )
    def test_drag_creation_matches_direct_assignment(self, x1, y1, x2, y2):
        """Dragging from A to B lands where set_roi_bounds(A, B) would.

        Two independent code paths -- start/update/finish versus a direct set --
        normalise the same coordinates, so they are free to drift apart.
        """
        dragged = ROIManager()
        dragged.start_roi_creation(x1, y1)
        dragged.update_roi_creation(x2, y2)
        dragged.finish_roi_creation()

        direct = ROIManager()
        direct.set_roi_bounds(x1, y1, x2, y2)

        assert dragged.get_roi_bounds() == direct.get_roi_bounds()

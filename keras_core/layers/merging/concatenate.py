from keras_core import ops
from keras_core.api_export import keras_core_export
from keras_core.layers.merging.base_merge import Merge


@keras_core_export("keras_core.layers.Concatenate")
class Concatenate(Merge):
    """Concatenates a list of inputs.

    It takes as input a list of tensors, all of the same shape except
    for the concatenation axis, and returns a single tensor that is the
    concatenation of all inputs.

    Examples:

    >>> x = np.arange(20).reshape(2, 2, 5)
    >>> y = np.arange(20, 30).reshape(2, 1, 5)
    >>> keras_core.layers.Concatenate(axis=1)([x, y])

    Usage in a Keras model:

    >>> x1 = keras_core.layers.Dense(8)(np.arange(10).reshape(5, 2))
    >>> x2 = keras_core.layers.Dense(8)(np.arange(10, 20).reshape(5, 2))
    >>> y = keras_core.layers.Concatenate()([x1, x2])

    Args:
        axis: Axis along which to concatenate.
        **kwargs: Standard layer keyword arguments.

    Returns:
        A tensor, the concatenation of the inputs alongside axis `axis`.
    """

    def __init__(self, axis=-1, **kwargs):
        super().__init__(**kwargs)
        self.axis = axis
        self.supports_masking = True
        self._reshape_required = False

    def build(self, input_shape):
        # Used purely for shape validation.
        if len(input_shape) < 1 or not isinstance(input_shape[0], tuple):
            raise ValueError(
                "A `Concatenate` layer should be called on a list of "
                f"at least 1 input. Received: input_shape={input_shape}"
            )
        if all(shape is None for shape in input_shape):
            return

        reduced_inputs_shapes = [list(shape) for shape in input_shape]
        shape_set = set()

        for i in range(len(reduced_inputs_shapes)):
            del reduced_inputs_shapes[i][self.axis]
            shape_set.add(tuple(reduced_inputs_shapes[i]))

        if len(shape_set) != 1:
            err_msg = (
                "A `Concatenate` layer requires inputs with matching shapes "
                "except for the concatenation axis. "
                f"Received: input_shape={input_shape}"
            )
            # Make sure all the shapes have same ranks.
            ranks = set(len(shape) for shape in shape_set)
            if len(ranks) != 1:
                raise ValueError(err_msg)
            # Get the only rank for the set.
            (rank,) = ranks
            for axis in range(rank):
                # Skip the Nones in the shape since they are dynamic, also the
                # axis for concat has been removed above.
                unique_dims = set(
                    shape[axis]
                    for shape in shape_set
                    if shape[axis] is not None
                )
                if len(unique_dims) > 1:
                    raise ValueError(err_msg)
        self.built = True

    def _merge_function(self, inputs):
        return ops.concatenate(inputs, axis=self.axis)

    def compute_output_shape(self, input_shape):
        if (not isinstance(input_shape, (tuple, list))) or (
            not isinstance(input_shape[0], (tuple, list))
        ):
            raise ValueError(
                "A `Concatenate` layer should be called on a list of inputs. "
                f"Received: input_shape={input_shape}"
            )
        input_shapes = input_shape
        output_shape = list(input_shapes[0])

        for shape in input_shapes[1:]:
            if output_shape[self.axis] is None or shape[self.axis] is None:
                output_shape[self.axis] = None
                break
            output_shape[self.axis] += shape[self.axis]
        return tuple(output_shape)

    def compute_mask(self, inputs, mask=None):
        if mask is None:
            return None
        if not isinstance(mask, (tuple, list)):
            raise ValueError(f"`mask` should be a list. Received mask={mask}")
        if not isinstance(inputs, (tuple, list)):
            raise ValueError(
                f"`inputs` should be a list. Received: inputs={inputs}"
            )
        if len(mask) != len(inputs):
            raise ValueError(
                "The lists `inputs` and `mask` should have the same length. "
                f"Received: inputs={inputs} of length {len(inputs)}, and "
                f"mask={mask} of length {len(mask)}"
            )
        if all(m is None for m in mask):
            return None
        # Make a list of masks while making sure
        # the dimensionality of each mask
        # is the same as the corresponding input.
        masks = []
        for input_i, mask_i in zip(inputs, mask):
            if mask_i is None:
                # Input is unmasked. Append all 1s to masks,
                masks.append(ops.ones_like(input_i, dtype="bool"))
            elif mask_i.ndim < input_i.ndim:
                # Mask is smaller than the input, expand it
                masks.append(ops.expand_dims(mask_i, axis=-1))
            else:
                masks.append(mask_i)
        concatenated = ops.concatenate(masks, axis=self.axis)
        return ops.all(concatenated, axis=-1, keepdims=False)

    def get_config(self):
        config = {"axis": self.axis}
        base_config = super().get_config()
        return dict(list(base_config.items()) + list(config.items()))


@keras_core_export("keras_core.layers.concatenate")
def concatenate(inputs, axis=-1, **kwargs):
    """Functional interface to the `Concatenate` layer.

    Args:
        inputs: A list of input tensors.
        axis: Concatenation axis.
        **kwargs: Standard layer keyword arguments.

    Returns:
        A tensor, the concatenation of the inputs alongside axis `axis`.
    """
    return Concatenate(axis=axis, **kwargs)(inputs)

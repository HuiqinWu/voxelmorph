from tensorflow import keras 
import h5py
import json
import inspect
import functools


def store_config_args(func):
    """
    Class-method decorator that saves every argument provided to the
    function as a dictionary in 'self.config'. This is used to assist
    model loading - see LoadableModel.
    """

    attrs, varargs, varkw, defaults = inspect.getargspec(func)

    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        self.config = {}

        # first save the default values
        if defaults:
            for attr, val in zip(reversed(attrs), reversed(defaults)):
                self.config[attr] = val

        # next handle positional args
        for attr, val in zip(attrs[1:], args):
            self.config[attr] = val

        # lastly handle keyword args
        if kwargs:
            for attr, val in kwargs.items():
                self.config[attr] = val

        return func(self, *args, **kwargs)
    return wrapper


class LoadableModel(keras.Model):
    """
    Base class for easy keras model loading without having to manually
    specify the architecture configuration at load time.

    If the get_config() method is defined for a keras.Model subclass, the saved
    H5 model will automatically store the returned config. This way, we can cache
    the arguments used to the construct the initial network, so that we can construct
    the exact same network when loading from file. The arguments provided to __init__
    are automatically saved into the object (in self.config) if the __init__ method
    is decorated with the @store_config_args utility.
    """

    # this constructor just functions as a check to make sure that every
    # LoadableModel subclass has provided an internal config parameter
    # either manually or via store_config_args
    def __init__(self, *args, **kwargs):
        if not hasattr(self, 'config'):
            raise RuntimeError('models that inherit from LoadableModel must decorate the constructor with @store_config_args')
        super().__init__(*args, **kwargs)

    def get_config(self):
        """
        Returns the internal config params used to initialize the model.
        Loadable keras models expect this function to be defined.
        """
        return self.config

    @classmethod
    def from_config(cls, config, custom_objects=None):
        """
        Constructs the model from the config arguments provided.
        """
        return cls(**config)

    @classmethod
    def load(cls, path, by_name=False):
        """
        Loads model config and weights from an H5 file. This first constructs a model using
        the config parameters stored in the H5 and then seperately loads the weights. The
        keras load function is not used directly because it expects all training parameters,
        like custom losses, to be defined, which we don't want to do.
        """
        with h5py.File(path, mode='r') as f:
            config = json.loads(f.attrs['model_config'].decode('utf-8'))['config']
        model = cls(**config)
        model.load_weights(path, by_name=by_name)
        return model

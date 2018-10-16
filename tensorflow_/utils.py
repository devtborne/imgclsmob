import numpy as np
import tensorflow as tf

from .model_provider import get_model


def save_model_params(sess,
                      file_path):
    # assert file_path.endswith('.npz')
    param_dict = {v.name: v.eval(sess) for v in tf.global_variables()}
    np.savez_compressed(file_path, **param_dict)


def load_model_params(net,
                      param_dict,
                      sess,
                      ignore_missing=False):
    for param_name, param_data in param_dict:
        with tf.variable_scope(param_name, reuse=True):
            try:
                var = tf.get_variable(param_name)
                sess.run(var.assign(param_data))
            except ValueError:
                if not ignore_missing:
                    raise


def prepare_model(model_name,
                  classes,
                  use_pretrained):
    kwargs = {'pretrained': use_pretrained,
              'classes': classes}

    net = get_model(model_name, **kwargs)

    x = tf.placeholder(
        dtype=tf.float32,
        shape=(None, 3, 224, 224),
        name='xx')
    y_net = net(x)

    return y_net
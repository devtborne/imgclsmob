"""
    DenseNet, implemented in Gluon.
    Original paper: 'Densely Connected Convolutional Networks'
"""

from mxnet import cpu
from mxnet.gluon import nn, HybridBlock


class ConvBlock(HybridBlock):

    def __init__(self,
                 in_channels,
                 out_channels,
                 kernel_size,
                 strides,
                 padding,
                 bn_use_global_stats,
                 **kwargs):
        super(ConvBlock, self).__init__(**kwargs)
        with self.name_scope():
            self.bn = nn.BatchNorm(
                in_channels=in_channels,
                use_global_stats=bn_use_global_stats)
            self.activ = nn.Activation('relu')
            self.conv = nn.Conv2D(
                channels=out_channels,
                kernel_size=kernel_size,
                strides=strides,
                padding=padding,
                use_bias=False,
                in_channels=in_channels)

    def hybrid_forward(self, F, x):
        x = self.bn(x)
        x = self.activ(x)
        x = self.conv(x)
        return x


def conv1x1_block(in_channels,
                  out_channels,
                  bn_use_global_stats):
    return ConvBlock(
        in_channels=in_channels,
        out_channels=out_channels,
        kernel_size=1,
        strides=1,
        padding=0,
        bn_use_global_stats=bn_use_global_stats)


def conv3x3_block(in_channels,
                  out_channels,
                  bn_use_global_stats):
    return ConvBlock(
        in_channels=in_channels,
        out_channels=out_channels,
        kernel_size=3,
        strides=1,
        padding=1,
        bn_use_global_stats=bn_use_global_stats)


class TransitionBlock(HybridBlock):

    def __init__(self,
                 in_channels,
                 out_channels,
                 bn_use_global_stats,
                 **kwargs):
        super(TransitionBlock, self).__init__(**kwargs)
        with self.name_scope():
            self.conv = conv1x1_block(
                in_channels=in_channels,
                out_channels=out_channels,
                bn_use_global_stats=bn_use_global_stats)
            self.pool = nn.MaxPool2D(
                pool_size=2,
                strides=2,
                padding=0)

    def hybrid_forward(self, F, x):
        x = self.conv(x)
        x = self.pool(x)
        return x


class DenseUnit(HybridBlock):

    def __init__(self,
                 in_channels,
                 out_channels,
                 bn_use_global_stats,
                 dropout_rate,
                 **kwargs):
        super(DenseUnit, self).__init__(**kwargs)
        self.use_dropout = (dropout_rate != 0.0)
        bn_size = 4
        mid_channels = out_channels * bn_size

        with self.name_scope():
            self.conv1 = conv1x1_block(
                in_channels=in_channels,
                out_channels=mid_channels,
                bn_use_global_stats=bn_use_global_stats)
            self.conv2 = conv3x3_block(
                in_channels=mid_channels,
                out_channels=out_channels,
                bn_use_global_stats=bn_use_global_stats)
            if self.use_dropout:
                self.dropout = nn.Dropout(rate=dropout_rate)

    def hybrid_forward(self, F, x):
        identity = x
        x = self.conv1(x)
        x = self.conv2(x)
        if self.use_dropout:
            x = self.dropout(x)
        x = F.concat(x, identity, dim=1)
        return x


class DenseInitBlock(HybridBlock):

    def __init__(self,
                 in_channels,
                 out_channels,
                 bn_use_global_stats,
                 **kwargs):
        super(DenseInitBlock, self).__init__(**kwargs)
        with self.name_scope():
            self.conv = nn.Conv2D(
                channels=out_channels,
                kernel_size=7,
                strides=2,
                padding=3,
                use_bias=False,
                in_channels=in_channels)
            self.bn = nn.BatchNorm(
                in_channels=out_channels,
                use_global_stats=bn_use_global_stats)
            self.activ = nn.Activation('relu')
            self.pool = nn.MaxPool2D(
                pool_size=3,
                strides=2,
                padding=1)

    def hybrid_forward(self, F, x):
        x = self.conv(x)
        x = self.bn(x)
        x = self.activ(x)
        x = self.pool(x)
        return x


class DenseNet(HybridBlock):

    def __init__(self,
                 channels,
                 init_block_channels,
                 growth_rate,
                 bn_use_global_stats=False,
                 in_channels=3,
                 classes=1000,
                 **kwargs):
        super(DenseNet, self).__init__(**kwargs)
        dropout_rate = 0

        with self.name_scope():
            self.features = nn.HybridSequential(prefix='')
            self.features.add(DenseInitBlock(
                in_channels=in_channels,
                out_channels=init_block_channels,
                bn_use_global_stats=bn_use_global_stats))
            in_channels = init_block_channels
            for i, channels_per_stage in enumerate(channels):
                stage = nn.HybridSequential(prefix='stage{}_'.format(i + 1))
                with stage.name_scope():
                    for j, out_channels in enumerate(channels_per_stage):
                        if (j == 0) and (i != 0):
                            stage.add(TransitionBlock(
                                in_channels=in_channels,
                                out_channels=out_channels,
                                bn_use_global_stats=bn_use_global_stats))
                            in_channels = out_channels
                        stage.add(DenseUnit(
                            in_channels=in_channels,
                            out_channels=growth_rate,
                            bn_use_global_stats=bn_use_global_stats,
                            dropout_rate=dropout_rate))
                        in_channels = out_channels
                self.features.add(stage)
            self.features.add(nn.AvgPool2D(
                pool_size=7,
                strides=1))

            self.output = nn.HybridSequential(prefix='')
            self.output.add(nn.Flatten())
            self.output.add(nn.Dense(
                units=classes,
                in_units=in_channels))

    def hybrid_forward(self, F, x):
        x = self.features(x)
        x = self.output(x)
        return x


def get_densenet(num_layers,
                 pretrained=False,
                 ctx=cpu(),
                 **kwargs):
    if num_layers == 121:
        init_block_channels = 64
        growth_rate = 32
        layers = [6, 12, 24, 16]
    elif num_layers == 161:
        init_block_channels = 96
        growth_rate = 48
        layers = [6, 12, 36, 24]
    elif num_layers == 169:
        init_block_channels = 64
        growth_rate = 32
        layers = [6, 12, 32, 32]
    elif num_layers == 201:
        init_block_channels = 64
        growth_rate = 32
        layers = [6, 12, 48, 32]
    else:
        raise ValueError("Unsupported DenseNet version with number of layers {}".format(num_layers))

    channels = [[ci] * li for (ci, li) in zip(growth_rate, layers)]
    from functools import reduce
    channels = reduce(lambda x, y: x + [(x[-1] + y * growth_rate) // 2], layers, [init_block_channels])[1:]

    if pretrained:
        raise ValueError("Pretrained model is not supported")

    return DenseNet(
        channels=channels,
        init_block_channels=init_block_channels,
        growth_rate=growth_rate,
        **kwargs)


def densenet121(**kwargs):
    return get_densenet(121, **kwargs)


def densenet161(**kwargs):
    return get_densenet(161, **kwargs)


def densenet169(**kwargs):
    return get_densenet(169, **kwargs)


def densenet201(**kwargs):
    return get_densenet(201, **kwargs)


def _test():
    import numpy as np
    import mxnet as mx

    global TESTING
    TESTING = True

    models = [
        densenet121,
        densenet161,
        densenet169,
        densenet201,
    ]

    for model in models:

        net = model()

        ctx = mx.cpu()
        net.initialize(ctx=ctx)

        net_params = net.collect_params()
        weight_count = 0
        for param in net_params.values():
            if (param.shape is None) or (not param._differentiable):
                continue
            weight_count += np.prod(param.shape)
        assert (model != densenet121 or weight_count == 7978856)

        x = mx.nd.zeros((1, 3, 224, 224), ctx=ctx)
        y = net(x)
        assert (y.shape == (1, 1000))


if __name__ == "__main__":
    _test()


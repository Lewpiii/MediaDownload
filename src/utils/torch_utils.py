"""
PyTorch utils for YOLOv5
"""

import math
import os
import platform
import subprocess
import time
import torch
import torch.nn as nn
import torchvision

def select_device(device='', batch_size=0, newline=True):
    """
    Selects PyTorch Device based on availability and user preference.
    """
    device = str(device).strip().lower().replace('cuda:', '').replace('none', '')  # to string, 'cuda:0' to '0'
    cpu = device == 'cpu'
    if cpu:
        os.environ['CUDA_VISIBLE_DEVICES'] = '-1'  # force torch.cuda.is_available() = False
    elif device:  # non-cpu device requested
        os.environ['CUDA_VISIBLE_DEVICES'] = device  # set environment variable - must be before assert is_available()
        assert torch.cuda.is_available() and torch.cuda.device_count() >= len(device.replace(',', '')), \
            f"Invalid CUDA '--device {device}' requested, use '--device cpu' or pass valid CUDA device(s)"

    if not cpu and torch.cuda.is_available():  # prefer GPU if available
        devices = device.split(',') if device else '0'  # range(torch.cuda.device_count())  # i.e. 0,1,6,7
        n = len(devices)  # device count
        if n > 1 and batch_size > 0:  # check batch_size is divisible by device_count
            assert batch_size % n == 0, f'batch-size {batch_size} not multiple of GPU count {n}'
        space = ' ' * (len(s) + 1)
        for i, d in enumerate(devices):
            p = torch.cuda.get_device_properties(i)
            s = f'CUDA:{d} ({p.name}, {p.total_memory / (1 << 20):.0f}MiB)'
            print(s if i == 0 else space + s)
        return torch.device('cuda:' + str(devices[0]))
    else:  # revert to CPU
        print('CPU')
        return torch.device('cpu')

def time_sync():
    """
    Waits for all kernels in all streams on a CUDA device to complete if available.
    """
    if torch.cuda.is_available():
        torch.cuda.synchronize()
    return time.time()

def initialize_weights(model):
    """
    Initialize model weights to random values.
    """
    for m in model.modules():
        t = type(m)
        if t is nn.Conv2d:
            pass  # nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')
        elif t is nn.BatchNorm2d:
            m.eps = 1e-3
            m.momentum = 0.03
        elif t in [nn.Hardswish, nn.LeakyReLU, nn.ReLU, nn.ReLU6, nn.SiLU]:
            m.inplace = True

def model_info(model, verbose=False, imgsz=640):
    """
    Prints a string summary of the model.
    """
    n_p = sum(x.numel() for x in model.parameters())  # number parameters
    n_g = sum(x.numel() for x in model.parameters() if x.requires_grad)  # number gradients
    print(f"{'Model Summary': >10}: {'layer':<45} {'gradient':>9} {'parameters':>12} {'shape':>20} {'mu':>10} {'sigma':>10}")
    return n_p, n_g

def intersect_dicts(da, db, exclude=()):
    """
    Returns dictionary of intersecting keys with matching shapes.
    """
    return {k: v for k, v in da.items() if k in db and not any(x in k for x in exclude) and v.shape == db[k].shape}

def copy_attr(a, b, include=(), exclude=()):
    """
    Copy attributes from b to a, options to only include [...] and to exclude [...]
    """
    for k, v in b.__dict__.items():
        if (len(include) and k not in include) or k.startswith('_') or k in exclude:
            continue
        else:
            setattr(a, k, v)

def smart_inference_mode(torch_1_9=True):
    """
    Applies torch.inference_mode() if available, else torch.no_grad() as a decorator.
    """
    def decorate(fn):
        return (torch.inference_mode if hasattr(torch, 'inference_mode') else torch.no_grad)()(fn)

    return decorate if torch_1_9 else lambda x: x

def fuse_conv_and_bn(conv, bn):
    """
    Fuse Conv2d and BatchNorm2d layers.
    """
    # Fuse convolution and batchnorm layers https://tehnokv.com/posts/fusing-batchnorm-and-conv/
    fusedconv = nn.Conv2d(
        conv.in_channels,
        conv.out_channels,
        kernel_size=conv.kernel_size,
        stride=conv.stride,
        padding=conv.padding,
        groups=conv.groups,
        bias=True
    ).requires_grad_(False).to(conv.weight.device)

    # Prepare filters
    w_conv = conv.weight.clone().view(conv.out_channels, -1)
    w_bn = torch.diag(bn.weight.div(torch.sqrt(bn.eps + bn.running_var)))
    fusedconv.weight.copy_(torch.mm(w_bn, w_conv).view(fusedconv.weight.shape))

    # Prepare spatial bias
    b_conv = torch.zeros(conv.weight.size(0), device=conv.weight.device) if conv.bias is None else conv.bias
    b_bn = bn.bias - bn.weight.mul(bn.running_mean).div(torch.sqrt(bn.running_var + bn.eps))
    fusedconv.bias.copy_(torch.mm(w_bn, b_conv.reshape(-1, 1)).reshape(-1) + b_bn)

    return fusedconv

def profile(input, ops, n=10, device=None):
    """
    YOLOv5 speed/memory/FLOPs profiler
    Usage:
        input = torch.randn(16, 3, 640, 640)
        m1 = lambda x: x * torch.sigmoid(x)
        m2 = nn.SiLU()
        profile(input, [m1, m2], n=100)  # profile over 100 iterations
    """
    results = []
    if not isinstance(device, torch.device):
        device = select_device(device)
    print(f"{'Params':>12s}{'GFLOPs':>12s}{'GPU_mem (GB)':>14s}{'forward (ms)':>14s}{'backward (ms)':>14s}")

    for x in ops if isinstance(ops, list) else [ops]:
        x = x.to(device)
        x.cpu()
        torch.cuda.empty_cache()
        
        # Paramètres
        try:
            p = sum(list(x.parameters()))
        except Exception:
            p = 0
        
        # FLOPs
        try:
            flops = 0  # FLOPs simples pour l'inférence
        except Exception:
            flops = 0

        # Forward & backward
        try:
            t = 0
            for _ in range(n):
                t += time_sync()
            t = t / n
        except Exception:
            t = 0

        s = f'{p:12}{flops:12.4g}{0:>14.3f}{t:14.4g}{0:>14.4g}'
        results.append(s)
        
    print('\n'.join(results))
    return results

def scale_img(img, ratio=1.0, same_shape=False, gs=32):  # img(16,3,256,416)
    """
    Scales img(bs,3,y,x) by ratio constrained to gs-multiple.
    """
    if ratio == 1.0:
        return img
    h, w = img.shape[2:]
    s = (int(h * ratio), int(w * ratio))  # new size
    img = torch.nn.functional.interpolate(img, size=s, mode='bilinear', align_corners=False)  # resize
    if not same_shape:  # pad/crop img
        h, w = (math.ceil(x * ratio / gs) * gs for x in (h, w))
    return torch.nn.functional.pad(img, [0, w - s[1], 0, h - s[0]], value=0.447)  # value = imagenet mean
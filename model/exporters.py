"""Writers for glTF-Binary (.glb), Wavefront (.obj/.mtl) and binary STL."""

from __future__ import annotations

import json
import os
import struct
import numpy as np


# --------------------------------------------------------------------------
# glTF 2.0 binary
# --------------------------------------------------------------------------

def write_glb(path, P, N, UV, F, textures=None, name='SP1_StemPlayer',
              scale=0.001, material_name='SP1 anodised aluminium'):
    """Write a self contained .glb.

    `P` is in millimetres; `scale` converts to the glTF convention of metres.
    `textures` maps 'base' / 'mr' / 'normal' to PNG byte strings.
    """
    pos = (np.asarray(P, dtype=np.float32) * scale)
    nrm = np.asarray(N, dtype=np.float32)
    uv = np.asarray(UV, dtype=np.float32)
    idx = np.asarray(F, dtype=np.uint32).reshape(-1)

    buffers = []
    views = []
    accessors = []
    offset = 0

    def add_view(data, target=None):
        nonlocal offset
        pad = (-len(data)) % 4
        data = data + b'\x00' * pad
        v = {'buffer': 0, 'byteOffset': offset, 'byteLength': len(data) - pad}
        if target is not None:
            v['target'] = target
        views.append(v)
        buffers.append(data)
        offset += len(data)
        return len(views) - 1

    def add_accessor(arr, ctype, atype, target, minmax=False):
        v = add_view(arr.tobytes(), target)
        a = {'bufferView': v, 'componentType': ctype, 'count': int(arr.shape[0]),
             'type': atype}
        if minmax:
            a['min'] = [float(x) for x in arr.min(axis=0)]
            a['max'] = [float(x) for x in arr.max(axis=0)]
        accessors.append(a)
        return len(accessors) - 1

    ARRAY_BUFFER, ELEMENT_ARRAY_BUFFER = 34962, 34963
    a_pos = add_accessor(pos, 5126, 'VEC3', ARRAY_BUFFER, minmax=True)
    a_nrm = add_accessor(nrm, 5126, 'VEC3', ARRAY_BUFFER)
    a_uv = add_accessor(uv, 5126, 'VEC2', ARRAY_BUFFER)
    a_idx = add_accessor(idx.reshape(-1, 1), 5125, 'SCALAR', ELEMENT_ARRAY_BUFFER)

    images, samplers, gtex = [], [], []
    pbr = {'baseColorFactor': [1, 1, 1, 1], 'metallicFactor': 1.0,
           'roughnessFactor': 1.0}
    material = {'name': material_name, 'pbrMetallicRoughness': pbr,
                'doubleSided': False}

    if textures:
        samplers.append({'magFilter': 9729, 'minFilter': 9987,
                         'wrapS': 33071, 'wrapT': 33071})
        order = [('base', 'baseColorTexture'), ('mr', 'metallicRoughnessTexture'),
                 ('normal', 'normalTexture')]
        for key, slot in order:
            png = textures.get(key)
            if png is None:
                continue
            v = add_view(png)
            images.append({'bufferView': v, 'mimeType': 'image/png',
                           'name': f'sp1_{key}'})
            gtex.append({'sampler': 0, 'source': len(images) - 1})
            ref = {'index': len(gtex) - 1, 'texCoord': 0}
            if slot == 'normalTexture':
                ref['scale'] = 1.0
                material['normalTexture'] = ref
            else:
                pbr[slot] = ref

    blob = b''.join(buffers)
    gltf = {
        'asset': {'version': '2.0',
                  'generator': 'sp1-stem-player-3d-model (photogrammetric)'},
        'scene': 0,
        'scenes': [{'nodes': [0]}],
        'nodes': [{'mesh': 0, 'name': name}],
        'meshes': [{'name': name, 'primitives': [{
            'attributes': {'POSITION': a_pos, 'NORMAL': a_nrm, 'TEXCOORD_0': a_uv},
            'indices': a_idx, 'material': 0, 'mode': 4}]}],
        'materials': [material],
        'buffers': [{'byteLength': len(blob)}],
        'bufferViews': views,
        'accessors': accessors,
    }
    if images:
        gltf['images'] = images
        gltf['samplers'] = samplers
        gltf['textures'] = gtex

    js = json.dumps(gltf, separators=(',', ':')).encode('utf-8')
    js += b' ' * ((-len(js)) % 4)
    blob += b'\x00' * ((-len(blob)) % 4)

    total = 12 + 8 + len(js) + 8 + len(blob)
    with open(path, 'wb') as fh:
        fh.write(b'glTF')
        fh.write(struct.pack('<II', 2, total))
        fh.write(struct.pack('<I', len(js))); fh.write(b'JSON'); fh.write(js)
        fh.write(struct.pack('<I', len(blob))); fh.write(b'BIN\x00'); fh.write(blob)
    return total


# --------------------------------------------------------------------------
# Wavefront OBJ
# --------------------------------------------------------------------------

def write_obj(path, P, N, UV, F, mtl_name='sp1_stem_player.mtl',
              material='sp1_aluminium'):
    base = os.path.splitext(path)[0]
    with open(path, 'w') as fh:
        fh.write('# Prototype SP-1 Stem Player - units: millimetres\n')
        fh.write(f'mtllib {mtl_name}\n')
        fh.write('o SP1_StemPlayer\n')
        np.savetxt(fh, P, fmt='v %.5f %.5f %.5f')
        np.savetxt(fh, UV, fmt='vt %.6f %.6f')
        np.savetxt(fh, N, fmt='vn %.5f %.5f %.5f')
        fh.write(f'usemtl {material}\n')
        f1 = F + 1
        tri = np.column_stack([f1[:, 0], f1[:, 0], f1[:, 0],
                               f1[:, 1], f1[:, 1], f1[:, 1],
                               f1[:, 2], f1[:, 2], f1[:, 2]])
        np.savetxt(fh, tri, fmt='f %d/%d/%d %d/%d/%d %d/%d/%d')

    with open(base + '.mtl', 'w') as fh:
        fh.write(f'newmtl {material}\n')
        fh.write('Ka 0.00 0.00 0.00\nKd 0.91 0.90 0.88\nKs 0.60 0.60 0.58\n')
        fh.write('Ns 90\nd 1.0\nillum 2\n')
        fh.write('map_Kd ../textures/sp1_base.png\n')
        fh.write('map_Bump -bm 1.0 ../textures/sp1_normal.png\n')
        fh.write('map_Ns ../textures/sp1_mr.png\n')


# --------------------------------------------------------------------------
# binary STL
# --------------------------------------------------------------------------

def write_stl(path, P, F):
    a, b, c = P[F[:, 0]], P[F[:, 1]], P[F[:, 2]]
    n = np.cross(b - a, c - a)
    ln = np.linalg.norm(n, axis=1, keepdims=True)
    n = n / np.maximum(ln, 1e-12)
    rec = np.zeros((len(F), 12), dtype=np.float32)
    rec[:, 0:3] = n; rec[:, 3:6] = a; rec[:, 6:9] = b; rec[:, 9:12] = c
    with open(path, 'wb') as fh:
        fh.write(b'Prototype SP-1 Stem Player - mm - photogrammetric model'.ljust(80, b' '))
        fh.write(struct.pack('<I', len(F)))
        payload = np.zeros((len(F), 50), dtype=np.uint8)
        payload[:, :48] = rec.view(np.uint8).reshape(len(F), 48)
        fh.write(payload.tobytes())


import io
from .fmt_details import Chunks, FORMAT_VERSION_3
from .xray_io import PackedWriter, ChunkedWriter
from .utils import AppError


class LevelDetails:
    def __init__(self):
        pass


def _get_image(cx, bpy_obj, xray_prop, prop_name):

    if xray_prop == '':
        raise AppError(
            'object "{0}" has no "{1}"'.format(bpy_obj.name, prop_name)
            )

    bpy_image = cx.bpy.data.images.get(xray_prop)
    if bpy_image == None:
        raise AppError(
            'cannot find "{0}" image: "{1}"'.format(
                prop_name, xray_prop
                )
            )

    return bpy_image


def _get_object(cx, bpy_obj, xray_prop, prop_name):

    if xray_prop == '':
        raise AppError(
            'object "{0}" has no "{1}"'.format(bpy_obj.name, prop_name)
            )

    bpy_object = cx.bpy.data.objects.get(xray_prop)
    if bpy_object == None:
        raise AppError(
            'cannot find "{0}": "{1}"'.format(
                prop_name, xray_prop
                )
            )

    return bpy_object


def _validate_object_type(bpy_obj, type, prop_name):
    if bpy_obj.type != type:
        raise AppError('"{0}" must be of type "{1}"'.format(prop_name, type))


def _get_level_details(cx, bpy_obj):

    x = bpy_obj.xray
    ld = LevelDetails()

    ld.format_version = 3

    ld.meshes_object = _get_object(
        cx, bpy_obj, x.details_meshes_object, 'Meshes Object'
        )
    _validate_object_type(ld.meshes_object, 'EMPTY', 'Meshes Object')

    ld.slots_base_object = _get_object(
        cx, bpy_obj, x.details_slots_base_object, 'Slots Base Object'
        )
    _validate_object_type(ld.slots_base_object, 'MESH', 'Slots Base Object')

    ld.slots_top_object = _get_object(
        cx, bpy_obj, x.details_slots_top_object, 'Slots Top Object'
        )
    _validate_object_type(ld.slots_top_object, 'MESH', 'Slots Top Object')

    if x.details_light_format == 'VERSION_2':
        raise AppError(
            'object "' + bpy_obj.name + '" has not supported lighting format'
            )
    else:
        ld.light_format = '1569-COP'

    ld.lights = _get_image(cx, bpy_obj, x.lights_image, 'Lights')
    ld.hemi = _get_image(cx, bpy_obj, x.hemi_image, 'Hemi')
    ld.shadows = _get_image(cx, bpy_obj, x.shadows_image, 'Shadows')
    ld.mesh_0 = _get_image(cx, bpy_obj, x.slots_mesh_0, 'Mesh 0')
    ld.mesh_1 = _get_image(cx, bpy_obj, x.slots_mesh_1, 'Mesh 1')
    ld.mesh_2 = _get_image(cx, bpy_obj, x.slots_mesh_2, 'Mesh 2')
    ld.mesh_3 = _get_image(cx, bpy_obj, x.slots_mesh_3, 'Mesh 3')

    return ld


def _write_header(cw, ld):
    pw = PackedWriter()
    pw.putf('<I', FORMAT_VERSION_3)
    pw.putf('<I', 0)    # meshes count
    pw.putf('<ii', ld.slots_offset_x, ld.slots_offset_y)
    pw.putf('<II', ld.slots_size_x, ld.slots_size_y)
    cw.put(Chunks.HEADER, pw)


def _calculate_slots_transforms(ld):

    base_slots = ld.slots_base_object
    bbox_base = base_slots.bound_box

    top_slots = ld.slots_top_object
    bbox_top = top_slots.bound_box

    for i in range(8):
        for ii in range(3):
            if ii != 2:
                coord_b = int(round(bbox_base[i][ii] / 2.0, 1))
                coord_t = int(round(bbox_top[i][ii] / 2.0, 1))

                if coord_b != coord_t:
                    raise AppError(
                        '"Slots Base Object" size not equal ' \
                        '"Slots Top Object" size'
                        )

    slots_bbox = (
        int(round(bbox_base[0][0] / 2.0, 1)),
        int(round(bbox_base[0][1] / 2.0, 1)),
        int(round(bbox_base[6][0] / 2.0, 1)),
        int(round(bbox_base[6][1] / 2.0, 1))
    )

    ld.slots_size_x = slots_bbox[2] - slots_bbox[0]
    ld.slots_size_y = slots_bbox[3] - slots_bbox[1]
    ld.slots_count = ld.slots_size_x * ld.slots_size_y

    if len(base_slots.data.polygons) != ld.slots_count:
        raise AppError(
            'Slots object "{0}" has an incorrect number of polygons. ' \
            'Must be {1}'.format(base_slots.name, ld.slots_count)
            )

    if len(top_slots.data.polygons) != ld.slots_count:
        raise AppError(
            'Slots object "{0}" has an incorrect number of polygons. ' \
            'Must be {1}'.format(top_slots.name, ld.slots_count)
            )

    ld.slots_offset_x = -slots_bbox[0]
    ld.slots_offset_y = -slots_bbox[1]


def _export(bpy_obj, cw, cx):
    ld = _get_level_details(cx, bpy_obj)

    _calculate_slots_transforms(ld)
    _write_header(cw, ld)


def export_file(bpy_obj, fpath, cx):
    with io.open(fpath, 'wb') as f:
        cw = ChunkedWriter()
        _export(bpy_obj, cw, cx)
        f.write(cw.data)

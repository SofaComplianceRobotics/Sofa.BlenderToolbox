#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Utils to import an animation in Blender from a TOML file
We use the script `animation_exporter.py` to generate the TOML file from a SOFA scene.
"""

import bpy
from math import radians
from array import array
from itertools import chain
from os.path import dirname, realpath, join as path_join, exists
from concurrent.futures import ThreadPoolExecutor, as_completed
import sys
import toml

sys.path.append(dirname(realpath(__file__)))

sys.path.pop()

BLENDER_4 = False

if BLENDER_4:
    import_options = {
        'forward_axis': 'Y',
        'up_axis': 'Z',
    }
else:
    import_options = {
        'split_mode': 'OFF',
        'axis_forward': 'Y',
        'axis_up': 'Z',
    }


def parse_monitor_file(path, frequency=1, type='deformable'):
    """Parse a SOFA monitor file to extract time series data for animation.
    Args:
        path (str): Path to the monitor file.
        frequency (int, optional): Sampling frequency to downsample the data. Defaults to 1 (no downsampling).
        type (str, optional): Type of object ('deformable' or 'rigid'). Defaults to 'deformable'.
    Returns:
        tuple: A tuple containing:
            - particles_ind (list): List of particle indices.
            - times (tuple): Tuple of time points.
            - data (tuple): Tuple of position/rotation data corresponding to each time point.
    """
    with open(path) as f:
        # Read header lines
        l1 = f.readline().strip()
        nb_part = next(int(x) for x in l1.split() if x.isdigit()) # number of particles
        l2 = f.readline().strip()
        particles_ind = [int(x) for x in l2.rsplit(' ', nb_part)[1:]] # particle indices
        # Read data lines
        data = f.readlines()

    # Parse data lines
    res = []
    data = [l.strip() for l in data if l.strip()]
    for l in data[::frequency]: # downsample according to frequency
        time = float(l.split(None, 1)[0]) # extract time
        d = [float(x) for x in l.split()[1:]] # extract data values
        if type == 'deformable': # deformable: positions only
            parts = list(zip(*(d[s::3] for s in range(3))))
        elif type == 'rigid': # rigid: position + quaternion
            parts = d[:3], [d[-1]] + d[3:-1]
        res.append((time, parts))
    times, data = zip(*res) 
    return particles_ind, times, data


def get_recording_info(path):
    """Extract recording information from a SOFA monitor file.
    Args:
        path (str): Path to the monitor file.
    Returns:        
        dict: A dictionary containing:
            - nb_points (int): Number of recorded points.
            - step (float): Time step between recordings.
            - total_time (float): Total recording time.
    """
    with open(path) as f:
        data = [x for x in f.readlines() if not x.startswith('#')] # skip comments
    total_time = float(data[-1].strip().split(None, 1)[0]) # last time point
    step = float(data[0].strip().split(None, 1)[0]) # first time point (assumed constant step)
    nb_points = len(data) 
    return dict(nb_points=nb_points, step=step, total_time=total_time)


def import_mesh(mesh_name):
    """Import an OBJ mesh into Blender.
    Args:
        mesh_name (str): Name of the mesh file (without extension).
    Returns:
        tuple: A tuple containing:
        - obj (bpy.types.Object): The imported Blender object.
    """
    path = mesh_name + ".obj"
    print("Importing ", path)
    if BLENDER_4:
        bpy.ops.wm.obj_import(filepath=path, **import_options)
        obj = bpy.context.selected_objects[0]
    else:
        bpy.ops.import_scene.obj(filepath=path, **import_options)
        obj = next(o for o in bpy.context.scene.objects if o.select_get())

    return obj


def init_anim(frames, start=None):
    """Initialize the animation frame range in Blender.
    Args:
        frames (int): Total number of frames for the animation.
        start (int, optional): Starting frame number. Defaults to None (starts at 1).
    """
    scene = bpy.context.scene
    scene.frame_start = start if start else 1
    scene.frame_end = frames


def add_animation_rigid(obj, times, data):
    """Add rigid body animation keyframes to a Blender object without using keyframe_insert.
    This builds f-curves and assigns keyframe points in batch using ``foreach_set``.
    Args:
        obj (bpy.types.Object): The Blender object to animate.
        times (tuple): Tuple of time points.
        data (tuple): Tuple of position/rotation data corresponding to each time point.
    """
    if not times or not data:
        return

    n = len(times)
    obj.rotation_mode = 'QUATERNION'

    # Extract per-frame positions and quaternions
    positions = [p for p, q in data]
    quaternions = [q for p, q in data]

    # Transpose to per-axis sequences (fast, in C)
    xs, ys, zs = zip(*positions)
    q0, q1, q2, q3 = zip(*quaternions)

    # Frames as floats 1..n
    frames = tuple(float(i) for i in range(1, n + 1))

    # Create a new action and f-curves
    action = bpy.data.actions.new(f"{obj.name}_RigidAnim")
    loc_fcurves = [action.fcurves.new(data_path="location", index=i) for i in range(3)]
    rot_fcurves = [action.fcurves.new(data_path="rotation_quaternion", index=i) for i in range(4)]

    # Helper to build interleaved (frame, value) array quickly
    def build_co_array(values):
        return array('f', chain.from_iterable(zip(frames, values)))

    co_x = build_co_array(xs)
    co_y = build_co_array(ys)
    co_z = build_co_array(zs)
    co_q0 = build_co_array(q0)
    co_q1 = build_co_array(q1)
    co_q2 = build_co_array(q2)
    co_q3 = build_co_array(q3)

    # Pre-allocate keyframe points and assign in batch
    for fcu in loc_fcurves + rot_fcurves:
        fcu.keyframe_points.add(n)

    loc_fcurves[0].keyframe_points.foreach_set("co", co_x)
    loc_fcurves[1].keyframe_points.foreach_set("co", co_y)
    loc_fcurves[2].keyframe_points.foreach_set("co", co_z)

    rot_fcurves[0].keyframe_points.foreach_set("co", co_q0)
    rot_fcurves[1].keyframe_points.foreach_set("co", co_q1)
    rot_fcurves[2].keyframe_points.foreach_set("co", co_q2)
    rot_fcurves[3].keyframe_points.foreach_set("co", co_q3)

    # Assign action to object animation data
    obj.animation_data_create()
    obj.animation_data.action = action


def add_animation_deformable(obj, indices, times, data):
    """Add deformable mesh animation keyframes to a Blender mesh.
    Args:       
        obj (bpy.types.Object): The Blender object to animate.
        indices (list): List of vertex indices to animate.
        times (tuple): Tuple of time points.
        data (tuple): Tuple of position data corresponding to each time point.
    """
    mesh = obj.data
    mesh.animation_data_create() # Ensure animation data exists
    action = bpy.data.actions.new("MeshAnimation") # Create a new action for the mesh
    
    data_path = "vertices[%d].co" # Data path template for vertex coordinates
    
    for vertex_id, positions in zip(indices, zip(*data)):
        n = len(positions)
        frames = tuple(float(i) for i in range(1, n + 1))

        # transpose positions -> three tuples: xs, ys, zs
        xs, ys, zs = zip(*positions)

        # build compact float arrays interleaving (frame, value)
        co_x = array('f', chain.from_iterable(zip(frames, xs)))
        co_y = array('f', chain.from_iterable(zip(frames, ys)))
        co_z = array('f', chain.from_iterable(zip(frames, zs)))

        # create F-curves and pre-add keyframe points
        fcu_x, fcu_y, fcu_z = [action.fcurves.new(data_path % vertex_id, index=i) for i in range(3)]
        for fcu in (fcu_x, fcu_y, fcu_z):
            fcu.keyframe_points.add(n)

        # apply in main thread with foreach_set
        fcu_x.keyframe_points.foreach_set("co", co_x)
        fcu_y.keyframe_points.foreach_set("co", co_y)
        fcu_z.keyframe_points.foreach_set("co", co_z)
    
    mesh.animation_data.action = action # Assign the action to the mesh


_mesh_cache = {}
def import_mesh_cached(mesh_name):
    """
    Import the mesh file named mesh_name.obj.
    If the mesh has already been loaded before, return the previously loaded data; else, load the file and return the data.
    
    Args:
        - mesh_name: str: name of the mesh file without the extension
    """
    # Returns an object linked to a cached mesh datablock (not animation)
    if mesh_name in _mesh_cache:
        mesh_data = _mesh_cache[mesh_name]
        new_obj = bpy.data.objects.new(name=mesh_name, object_data=mesh_data)
        bpy.context.collection.objects.link(new_obj)
        return new_obj

    obj = import_mesh(mesh_name)
    _mesh_cache[mesh_name] = obj.data
    return obj

def _process_object(config_obj, config_dir, frequency):
    """Worker function for parallel processing of a single object."""
    mesh_name = config_obj['mesh']
    obj_type = config_obj['type']
    
    # Parse monitor file
    if obj_type != 'static':
        filename = config_obj['monitor'] 
        if not exists(filename):
            filename = path_join(config_dir, filename)
        indices, times, data = parse_monitor_file(filename, frequency, type=obj_type)
    
        # Return data needed for animation setup
        return {
            'mesh_name': mesh_name,
            'obj_type': obj_type,
            'scale': config_obj.get('scale', [1, 1, 1]),
            'name': config_obj.get('name'),
            'translation': config_obj.get('translation', [0, 0, 0]),
            'rotation': config_obj.get('rotation', [0, 0, 0]),
            'indices': indices,
            'times': times,
            'data': data
        }
    else:
        return {
            'mesh_name': mesh_name,
            'obj_type': obj_type,
            'scale': config_obj.get('scale', [1, 1, 1]),
            'name': config_obj.get('name'),
            'translation': config_obj.get('translation', [0, 0, 0]),
            'rotation': config_obj.get('rotation', [0, 0, 0])
        }

    

def import_scene(config_path, frame_start=None, num_workers=16):
    """Import a scene into Blender based on a TOML configuration file.
    Args:
        config_path (str): Path to the TOML configuration file.
        frame_start (int, optional): Starting frame number for the animation. Defaults to None.
    """
    print("Importing Scene", config_path)
    config_dir = dirname(config_path)
    config = toml.load(config_path) # Load TOML configuration
    frequency = 1

    if not len(config.get('objects', [])):
        print("No object in the toml")
        exit(1)
    print("Loaded config file, found ", len(config.get('objects', [])), " objects")

    # Determine frame count from first object's monitor file
    for object in config.get('objects', []):
        first_monitor = object.get('monitor', None)
        if first_monitor is not None:
            if exists(first_monitor): 
                rec_infos = get_recording_info(first_monitor) # Extract recording info
                frames = config.get('frames', rec_infos['nb_points'] / frequency)
                break

    init_anim(frames, frame_start) # Initialize animation frame range
    print(f'Importing {int(frames)} animation frames', file=sys.stdout, flush=True)

    # Parallel monitor file parsing
    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = {executor.submit(_process_object, cfg, config_dir, frequency): cfg
               for cfg in config.get('objects', [])}

        for fut in as_completed(futures):
            try:
                result = fut.result()
            except Exception as e:
                print("Worker failed:", e, file=sys.stderr)
                continue

            obj = import_mesh_cached(result['mesh_name'])
            
            try:
                obj.scale = tuple(result['scale'])
            except:
                obj.scale = (result['scale'], result['scale'], result['scale'])

            if result['name']:
                obj.name = result['name']

            rotation = [radians(x) for x in result['rotation']]

            if result['obj_type'] == 'static':
                obj.location = result['translation']
                obj.rotation_euler = rotation
            else:
                obj.delta_location = result['translation']
                obj.delta_rotation_euler = rotation

                if result['obj_type'] == 'deformable':
                    add_animation_deformable(obj, result['indices'], result['times'], result['data'])
                elif result['obj_type'] == 'rigid':
                    add_animation_rigid(obj, result['times'], result['data'])
            
            print(f"Imported {obj.name}")


def usage():
    # Print usage instructions
    print('blender [preconfigured_scene.blend]'
          ' --python blender_importer.py -- scene_config.toml')


if __name__ == "__main__":
    try:
        # Parse command-line arguments
        scene_config_file, *extra_config = sys.argv[sys.argv.index("--") + 1:]
    except:
        usage()
        exit(1)

    import_scene(scene_config_file)

# Sofa.BlenderToolbox
Import SOFA animation to Blender using bpy (Blender Python API).

It imports geometry and animation data into Blender from a simple TOML scene description and accompanying mesh animation text files produced by SOFA (using the Monitor component).

This script is intended to be executed inside Blender's bundled Python interpreter (via --python) and manipulates bpy to import OBJ meshes, create keyframed animations for rigid and deformable objects.

## Requirements

Blender 3.6: see [documentation](https://docs.blender.org/api/3.6/)

## Usage

Run from shell where Blender's executable is accessible:
```bash
blender [preconfigured_scene.blend] --python blender_importer.py -- scene_config.toml
```

The "--" separator splits Blender's command-line arguments from the script's own arguments; the script reads the TOML path after the "--".

- `preconfigured_scene.blend` (optional): it will import the object from scene_config.toml into the preconfigured_scene.blend. Convenient when you already have a scene.
- `scene_config.toml`: the path to the file describing all the objects to import in the scene.

## Description

The scripts loads a TOML file describing a list of objects to import. Each object specifying at minimum a mesh (.obj) and a monitor file that contains recorded trajectories. Optional fields include type, scale, name, translation, rotation.

The High-level algoritm goes as follow:
- For each object:
    - Imports the associated OBJ mesh into the current Blender scene
    - Applies a uniform or per-axis scale if present
    - If object is 'static' applies fixed transform from translation/rotation values.
    - If object is 'rigid' or 'deformable' loads time series from the monitor file and creates Blender animation keyframes: translation + quaternion rotation for rigids, per-vertex animation (vertices[].co) for deformables.

- The frame range is set based on the recording length (or an explicit frame count
    in the TOML). The script supports an optional BLENDER_4 flag which switches the
    OBJ import operator argument names to the API used by Blender 4+.

### Example TOML (illustrative)

The following example will import two objects:
- an object named *Chair01* as a rigid with a trajectory described in the file *chair_monitor.txt*, its mesh is given by the *chair.obj* file and scaled by (x:1, y:1, z:1)
- an object named *Cloth01* as a deformable object and a trajectory file *cloth_monitor.txt*. Its mesh is the *cloth.obj* file and is scale by 1 on all axis.

```toml
[[objects]]
mesh = "chair"
monitor = "chair_monitor.txt"
type = "rigid"
scale = [1.0, 1.0, 1.0]
name = "Chair01"

[[objects]]
mesh = "cloth"
monitor = "cloth_monitor.txt"
type = "deformable"
scale = 1.0
name = "Cloth01"
```

### Good to know

**Linked Object**
For efficiency sake, if an object uses a mesh that already has been loaded before by another previous object, the created object will have its object-data [linked](https://docs.blender.org/manual/en/3.6/scene_layout/object/editing/link_transfer/index.html) to the previous object thanks to the `bpy.data.objects.new()` method.

**Paralellization**
To speed up the scene creation, the parsing of the monitor files is paralellized on 16 threads by default. To change this, you can set the `num_workers` parameter of the `import_scene` call line 400.
```python
import_scene(scene_config_file, num_workers=42)
```
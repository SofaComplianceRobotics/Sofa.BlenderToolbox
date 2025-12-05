# Sofa.BlenderToolbox
Utils to export the movement of objects in a SOFA scene as an animation in Blender.

## Requirements
- [SOFA Framework](https://www.sofa-framework.org/)
- [SofaValidation](https://github.com/sofa-framework/SofaValidation#) plugin
- Python 3.x
- `toml` package: `pip install toml`
- Blender (for rendering the exported animations)

## Usage
### Basic Workflow

- **Add Export Components to Nodes**: Configure SOFA nodes to export their animation data
- **Run Simulation**: Execute your SOFA simulation
- **Export Configuration**: Generate the TOML file with animation parameters
- **Import to Blender**: Use `blender_importer.py` to load the animation in Blender


# Animation Exporter ([animation_exporter.py](animation_exporter.py))

This module provides tools to bridge SOFA simulations with Blender. It automatically configures SOFA nodes to export mesh geometry and animation data, then generates a TOML configuration file that can be imported into Blender using the companion `blender_importer.py` script.

## Requirements
- [SOFA Framework](https://www.sofa-framework.org/)
- [SofaValidation](https://github.com/sofa-framework/SofaValidation#) plugin
- Python 3.x
- `toml` package: `pip install toml`

## Usage
1. Place the `animation_exporter.py` file somewhere accessible from your SOFA Python scene.
2. For each element of your scene that you want in the Blender animation use the `addExportComponentsToNode()` method.
3. At the end of your `createScene()` function, add a call to `exportAnimationConfig()`

Example
```python
import Sofa
import animation_exporter

def createScene(rootNode):
    # Create your SOFA scene...
    mechanicalNode = rootNode.addChild('MechanicalObject')
    topologyNode = rootNode.addChild('Topology')
    
    # Add export components for a deformable object
    addExportComponentsToNode(
        name='soft_body',
        mechaNode=mechanicalNode,
        topologyNode=topologyNode,
        objectType='deformable',
        template='Vec3',
        scale=[1.0, 1.0, 1.0],
        translation=[0, 0, 0]
    )
    
    # At the end of your scene setup
    exportAnimationConfig('animation_config.toml')
```

## Description
### addExportComponentsToNode
This function basically adds needed node for the export and 

# Blender Importer ([blender_importer.py](blender_importer.py))
Import SOFA animation to Blender using bpy (Blender Python API).

It imports geometry and animation data into Blender from a simple TOML scene description and accompanying mesh animation text files produced by SOFA (using the Monitor component).

This script is intended to be executed inside Blender's bundled Python interpreter (via --python) and manipulates bpy to import OBJ meshes, create keyframed animations for rigid and deformable objects.

## Requirements

Blender 3.6: see [documentation](https://docs.blender.org/api/3.6/)

To generate the toml file you will need a working SOFA scene and the SofaValidation plugin.

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

### Good-to-know implementation details

**Linked Object**

For efficiency sake, if an object uses a mesh that already has been loaded before by another previous object, the created object will have its object-data [linked](https://docs.blender.org/manual/en/3.6/scene_layout/object/editing/link_transfer/index.html) to the previous, cached, object thanks to the [`bpy.data.objects.new()`](https://docs.blender.org/api/3.6/bpy.types.BlendDataObjects.html#bpy.types.BlendDataObjects.new) method. Becausee of this cache mechanism, memory errors could happen if you load lots of different large meshes.

**Paralellization**

To speed up the scene creation, the parsing of the monitor files is paralellized on 16 threads by default. To change this, you can set the `num_workers` parameter of the `import_scene` call [line 400](https://github.com/SofaComplianceRobotics/Sofa.BlenderToolbox/blob/6eca9a42ccff0c3f9bcfcccba2f9c3b4da1e8f8b/blender_importer.py#L400).
```python
import_scene(scene_config_file, num_workers=42)
```
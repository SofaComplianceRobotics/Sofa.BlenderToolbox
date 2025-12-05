import toml
import os
import pathlib
import Sofa

"""
Utils to export the movement of objects in a SOFA scene as an animation in Blender
We use the script `blender_importer.py` to import the animation in Blender. This script (`blender_importer.py`) takes a toml file as input.
"""

outputDir: str = os.path.join(pathlib.Path.home(), '.sofa_runs', 'last_sofa_run') + os.sep

blenderAnimationConfig = {
        'frames': 2500,
        'frequency': 1,
        'objects': []
    }

def addExportComponentsToNode(name, mechaNode, indices=None, topologyNode=None, vertices=None, objectType='static', template="Rigid3", exportTriangles=True, meshFilename=None, scale=[1,1,1], translation=[0,0,0], rotation=[0,0,0]):
    """
    Adds the needed components (MeshExporter and Monitor) to export the animation of a node.

    This function prepares a SOFA node for animation export to Blender by adding the necessary
    export components. It handles both mesh export (via MeshExporter) and motion tracking 
    (via Monitor component). The function either exports a new mesh from the topology or 
    uses an existing mesh file.

    If `meshFilename`is given, no MeshExporter is added t

    Args:
        name (str): The name of the Blender object that will be created and also the name 
            of the mesh file if exported (without extension).
        mechaNode: The mechanical node containing the mechanical state (positions)
            to be monitored and exported for animation.
        indices (list[int], optional): List of vertex/DOF indices to monitor for animation.
            Required for non-static objects if verticesCount cannot be determined. 
            Defaults to None.
        topologyNode (optional): The topology node containing mesh connectivity information.
            Must have a Topology component. Required if meshFilename is not provided.
            Defaults to None.
        vertices (list, optional): The explicit positions of vertices in the topology.
            If provided, these will be used for mesh export instead of the topology's 
            default positions. Defaults to None.
        objectType (str, optional): Type of object animation - 'static' (no animation),
            'deformable' (per-vertex animation), or 'rigid' (rigid body transformation).
            Defaults to 'static'.
        template (str, optional): SOFA template type for the mechanical state (e.g., 
            "Rigid3", "Vec3"). Determines the data type for the Monitor component.
            Defaults to "Rigid3".
        exportTriangles (bool, optional): Whether to export triangle faces in the mesh.
            Set to False for point clouds or line meshes. Defaults to True.
        meshFilename (str, optional): Path to an existing mesh file to use instead of 
            exporting a new one. If None, a new mesh will be exported from topologyNode.
            Defaults to None.
        scale (list[float], optional): 3D scale factors [x, y, z] to apply to the object 
            in Blender. Defaults to [1, 1, 1].
        translation (list[float], optional): 3D translation offset [x, y, z] to apply to 
            the object in Blender. Defaults to [0, 0, 0].
        rotation (list[float], optional): 3D rotation angles [rx, ry, rz] in degrees to 
            apply to the object in Blender. Ignored for non-static objects. 
            Defaults to [0, 0, 0].

    Raises:
        ValueError: If neither meshFilename nor topologyNode is provided.
        ValueError: If objectType is not 'static' and both indices and verticesCount are None.

    Notes:
        - If meshFilename is not provided, a MeshExporter component is added to topologyNode
        - The exported mesh file will be saved in the outputDir with the given name
        - For non-static objects, rotation is always set to [0, 0, 0] as it's handled by animation
        - The function automatically determines indices for deformable objects if not provided
    """
    if meshFilename is None and topologyNode is None:
        raise ValueError("You need to provide one of `meshFilename` or `topologyNode`")
    
    verticesCount = None
    if meshFilename is None:
        meshFilename=outputDir + name # create a temporary obj file
        if vertices is None:
            topologyNode.addObject('MeshExporter',
                                exportAtBegin=True, 
                                filename=meshFilename,
                                format='obj',
                                triangles=exportTriangles
                                )
        else:
            topologyNode.addObject('MeshExporter',
                                    exportAtBegin=True, 
                                    filename=meshFilename,
                                    format='obj',
                                    triangles=exportTriangles,
                                    position=vertices
                                    )
        verticesCount = len(topologyNode.MeshExporter.position.value)

    if objectType!='static' and indices is None and verticesCount is None:
        raise ValueError("You need to provide `indices`")
    
    if indices is None:
        indices = list(range(verticesCount)) if objectType=='deformable' else [0]

    addObjectConfig(node=mechaNode, name=name,
                    scale=scale, 
                    translation=translation,
                    rotation=rotation if objectType == 'static' else [0, 0, 0],
                    objectType=objectType, 
                    template=template, 
                    indices=indices,
                    meshFilename=meshFilename
                    )

def addObjectConfig(node, name, template, objectType, meshFilename,
                    translation=[0, 0, 0], rotation=[0, 0, 0], scale=[1, 1, 1], indices=None, prefixPath=None):
    """
    Adds the TOML configuration for a given object to the global blenderAnimationConfig dictionary
    and creates a Monitor component for non-static objects.

    This function registers an object for Blender export by adding its configuration to the 
    global blenderAnimationConfig. For animated (non-static) objects, it also adds a Monitor 
    component to track position changes during simulation. The function handles path resolution
    for mesh files and ensures the SofaValidation plugin is loaded.

    Args:
        node: The SOFA node to which the Monitor component will be added (for non-static objects).
            Should contain a MechanicalObject component.
        name (str): Unique identifier for the object in Blender and for the monitor output files.
        template (str): SOFA template type for the Monitor component (e.g., "Rigid3", "Vec3", "Vec3d").
            Must match the MechanicalObject template of the node.
        objectType (str): Type of object - 'static' (no animation data exported), 'deformable' 
            (vertex-level animation), or 'rigid' (rigid body transformation).
        meshFilename (str): Path or filename of the mesh file (.obj). Can be relative or absolute.
            The function will attempt to resolve it relative to prefixPath if needed.
        translation (list[float], optional): 3D translation offset [x, y, z] to apply in Blender. 
            Defaults to [0, 0, 0].
        rotation (list[float], optional): 3D rotation angles [rx, ry, rz] in degrees to apply 
            in Blender. Defaults to [0, 0, 0].
        scale (list[float], optional): 3D scale factors [x, y, z] to apply in Blender. 
            Defaults to [1, 1, 1].
        indices (list[int], optional): Specific vertex/DOF indices to monitor. If None and 
            objectType is not 'static', monitors all DOFs in the mechanical state. 
            Defaults to None.
        prefixPath (str, optional): Base directory path to prepend to meshFilename for path 
            resolution. If None, defaults to "../../../../meshes" relative to this file. 
            Defaults to None.

    Side Effects:
        - Adds 'RequiredPlugin' component with name "SofaValidation" to root node if not present
        - For non-static objects: adds a Monitor component to the node that exports position 
          data to '{outputDir}/{name}_x.txt'

    Notes:
        - The Monitor component only exports positions, not velocities or forces
        - All numeric values (scale, translation, rotation) are converted to floats
        - Path resolution attempts to find mesh in prefixPath first, falls back to meshFilename
        - Monitor file is automatically named as '{name}_x.txt' in the outputDir
        - If indices is None for non-static objects, all DOFs from the mechanical state are monitored
    
    """

    rootnode = node.getRoot()
    if (rootnode.getObject("SofaValidation") == None):
        rootnode.addObject("RequiredPlugin", name="SofaValidation")

    # Handle path
    if prefixPath is None:
        prefixPath = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "meshes")
    path = os.path.join(prefixPath, meshFilename)
    path = pathlib.Path(path).as_posix()
    if not os.path.exists(path + '.obj'):
        path = meshFilename
    path = pathlib.Path(path).as_posix()

    objectConfig = {
        'mesh': path,
        'type': objectType,
        'name': name,
        'scale': [float(s) for s in scale]
    }

    objectConfig['translation'] = [float(t) for t in translation]
    objectConfig['rotation'] = [float(r) for r in rotation]    

    if objectType != 'static':
        objectConfig['monitor'] = os.path.join(outputDir, name + '_x.txt')
        node.addObject('Monitor', name="monitor"+name, template=template, listening=True, ExportPositions=True,
                    ExportVelocities=False,
                    ExportForces=False, indices=indices if indices is not None else list(range(node.getMechanicalState().size.value)), fileName=os.path.join(outputDir, name))
        
    blenderAnimationConfig['objects'].append(objectConfig)


def exportAnimationConfig(filename):
    """
    Exports the global blenderAnimationConfig dictionary to a TOML file for use with Blender importer.

    This function validates that all mesh files referenced in the animation configuration exist,
    then writes the complete configuration (including frames, frequency, and all object data)
    to a TOML file. This file is consumed by the `blender_importer.py` script to set up 
    the animation in Blender.

    Args:
        filename (str): Name of the output TOML file (e.g., "animation.toml"). The file will
            be created in the outputDir directory. If the file already exists, it will be 
            overwritten.

    Notes:
        - The function checks for mesh file existence by appending '.obj' extension
        - Missing mesh files are reported and the missing obj file is created
        - File is opened in 'w+' mode, creating the file if it doesn't exist or truncating if it does

    Example TOML output structure:
        frames = 2500
        frequency = 1
        
        [[objects]]
        mesh = "path/to/mesh.obj"
        type = "deformable"
        name = "object1"
        scale = [1.0, 1.0, 1.0]
        translation = [0.0, 0.0, 0.0]
        rotation = [0.0, 0.0, 0.0]
        monitor = "path/to/object1_x.txt"
    """
    for object in blenderAnimationConfig['objects']:
        path = object['mesh']
        if not os.path.exists(path+'.obj'):
            Sofa.msg_warning("Mesh file path does not exist so creating it: ", path)
            open(path+'.obj', 'w')

    with open(outputDir+filename, 'w+') as f:
        # Write toml file, overwriting if it exists
        toml.dump(blenderAnimationConfig, f)
        f.close()

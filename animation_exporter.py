import toml
import os
import pathlib
import Sofa

"""
Utils to render the animation in Blender
We use the script `blender_importer.py` to set up the animation in Blender. This script (`blender_importer.py`) takes a toml file as input.
"""

outputDir: str = os.path.join(pathlib.Path.home(), '.sofa_runs', 'last_sofa_run') + os.sep

blenderAnimationConfig = {
        'frames': 2500,
        'frequency': 1,
        'objects': []
    }

def addExportComponentsToNode(name, mechaNode, indices, topologyNode=None, vertices=None, objectType='static', template="Rigid3", exportTriangles=True, meshFilename=None, scale=[1,1,1], translation=[0,0,0], rotation=[0,0,0]):
    """
    Adds the needed components (MeshExporter and Monitor) to export the animation of a node.

    If `meshFilename`is given, no MeshExporter is added t

    Args:
        - name, 
        - mechaNode, 
        - visuNode: visual node used to export the mesh. It needs to contain a Topology component
        - vertices: the posisions of the vertices in the topology 
        - objectType, 
        - indices, 
        - template, 
        - exportTriangles=True, 
        - meshFilename=None, 
        - scale=[1,1,1], 
        - translation=[0,0,0], 
        - rotation=[0,0,0]
    """
    if meshFilename is None:
        meshFilename=outputDir + name # create a temporary obj file
        topologyNode.addObject('MeshExporter',
                            exportAtBegin=True, 
                            filename=meshFilename,
                            format='obj',
                            position=vertices,
                            triangles=exportTriangles
                            )

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
    Adds the toml description of a given object to the static params.scene.blenderAnimationConfig

    Args:
        - node
        - name
        - indices
        - template
        - objectType
        - meshFilename
        - translation
        - rotation
        - scale
        - prefixPath
    
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


# Export params.scene.blenderAnimationConfig
def exportAnimationConfig(filename):
    for object in blenderAnimationConfig['objects']:
        path = object['mesh']
        if not os.path.exists(path+'.obj'):
            Sofa.msg_error("Mesh file path does not exist: ", path)

    with open(outputDir+filename, 'w+') as f:
        # Write toml file, overwriting if it exists
        toml.dump(blenderAnimationConfig, f)
        f.close()

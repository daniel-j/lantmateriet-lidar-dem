#!/usr/bin/env python3

import sys
import os.path, glob
import subprocess
import json

input = sys.argv[1]
output = sys.argv[2]
buffer = int(sys.argv[3])
indir = os.path.dirname(input)
infile = os.path.basename(input)

group, ypos, xpos, size = os.path.splitext(infile)[0].split('_')
xpos = int(xpos)
ypos = int(ypos)
size = int(size)

def reader_las(filename):
    return { 'type':'readers.las', 'filename': filename, 'default_srs':'EPSG:3006' }

inputlist = [reader_las(input)]
inputs = [input]

# interpolate from a 3x3 grid
for y in (ypos-size, ypos, ypos+size):
    for x in (xpos-size, xpos, xpos+size):
        if x == xpos and y == ypos: continue
        path = os.path.join(indir, '*_' + str(y) + '_' + str(x) + '_' + str(size) + '.laz')
        result = glob.glob(path)
        if len(result) > 0:
            inputlist.append(reader_las(result[0]))
            inputs.append(result[0])

print('Input files:', *inputs)

print('Filtering point cloud...', output + '.laz')

pipeline_crop = {'pipeline': []}
pipeline_crop['pipeline'] += inputlist
pipeline_crop['pipeline'].append({ 'type': 'filters.crop', 'bounds': str(([xpos*100-buffer, xpos*100+buffer+size*100],[ypos*100-buffer,ypos*100+buffer+size*100])) })
pipeline_crop['pipeline'].append({ 'type': 'filters.range', 'limits': 'Classification[2:2], Classification[9:9]' })
pipeline_crop['pipeline'].append({ 'type': 'filters.sample', 'radius': 1.0 })
pipeline_crop['pipeline'].append(output + '.laz')

pdal_crop = subprocess.Popen(['pdal', 'pipeline', '--stdin', '--stream'], stdin=subprocess.PIPE)
pdal_crop.communicate(input=json.dumps(pipeline_crop).encode('utf-8'))
assert pdal_crop.returncode == 0


print('Rasterizing...', output)

pipeline_raster = {'pipeline': []}
pipeline_raster['pipeline'].append(output + '.laz')
pipeline_raster['pipeline'].append({ 'type': 'filters.delaunay' })
pipeline_raster['pipeline'].append({ 'type': 'filters.faceraster', 'resolution': 1.0, 'origin_x': xpos*100, 'origin_y': ypos*100, 'width': size*100, 'height': size*100 })
pipeline_raster['pipeline'].append({ 'type': 'writers.raster', 'filename': output, 'gdalopts': 'NUM_THREADS=ALL_CPUS,TILED=YES,COMPRESS=ZSTD' })

pdal_raster = subprocess.Popen(['pdal', 'pipeline', '--stdin'], stdin=subprocess.PIPE)
pdal_raster.communicate(input=json.dumps(pipeline_raster).encode('utf-8'))

assert pdal_raster.returncode == 0

# remove filtered point cloud
#os.remove(output + '.laz')

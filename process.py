#!/usr/bin/env python3

import sys
import os.path
import subprocess
import json
from osgeo import gdal

input = sys.argv[1]
output = sys.argv[2]
buffer = int(sys.argv[3])
indir = os.path.dirname(input)
topdir = os.path.dirname(os.path.dirname(indir))
infile = os.path.basename(input)

group, ypos, xpos, size = os.path.splitext(infile)[0].split('_')
xpos = int(xpos)
ypos = int(ypos)
size = int(size)

gdal.UseExceptions()

def reader_las(filename):
    return { 'type':'readers.las', 'filename': filename, 'default_srs':'EPSG:3006' }

inputlist = [reader_las(input)]
inputs = [input]

missingtiles = []

# interpolate from a 3x3 grid
for y in (ypos-size, ypos, ypos+size):
    for x in (xpos-size, xpos, xpos+size):
        if x == xpos and y == ypos: continue
        tilename = group + '_' + str(y) + '_' + str(x) + '_' + str(size) + '.laz'
        path = os.path.join(indir, tilename)
        found = False
        if not os.path.exists(path):
            pathborder = os.path.join(indir, 'border', tilename)
            if not os.path.exists(pathborder):
                missingtiles.append((tilename, (xpos - x)/size, (ypos - y)/size))
            else:
                print("Using border tile", tilename)
                path = pathborder
                found = True
        else:
            found = True
        if found:
            inputlist.append(reader_las(path))
            inputs.append(path)

print('Input files:', *inputs)
if len(missingtiles) > 0:
    print("Warning: Missing tiles:", *missingtiles)

print('Filtering input point clouds...', output + '.laz')

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
pipeline_raster['pipeline'].append({ 'type': 'writers.raster', 'filename': output + '.tmp.tif', 'gdalopts': 'NUM_THREADS=ALL_CPUS,COMPRESS=ZSTD' })

pdal_raster = subprocess.Popen(['pdal', 'pipeline', '--stdin'], stdin=subprocess.PIPE)
pdal_raster.communicate(input=json.dumps(pipeline_raster).encode('utf-8'))
assert pdal_raster.returncode == 0

raster = gdal.Open(output + '.tmp.tif', gdal.GA_Update)
rasterband = raster.GetRasterBand(1)
result = gdal.FillNodata(targetBand = rasterband, maskBand = None, maxSearchDist = 50, smoothingIterations = 0)
assert result == 0

newraster = gdal.GetDriverByName('COG').CreateCopy(output, raster, options = ['COMPRESS=ZSTD', 'NUM_THREADS=ALL_CPUS'])
newraster = None

raster = None

os.remove(output + '.tmp.tif')

# remove filtered point cloud
os.remove(output + '.laz')

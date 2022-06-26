#!/usr/bin/env python3
"""
import rasterio as rio
from rio_tiler.io import COGReader
from rio_tiler.profiles import img_profiles


with COGReader("dem.vrt") as cog:
    info = cog.info()
    print(info)
    print(info.nodata_type)

    img = cog.tile(69991, 39735, 17)


    content = img.render(img_format="GTiff", add_mask=False, compress="DEFLATE")
    with open("test.tif", "wb") as f:
        f.write(content)


"""


"""rio-tiler tile server."""

# usage: uvicorn tiler:app --reload

import os
from enum import Enum
from typing import Any, Dict, List, Optional
from types import DynamicClassAttribute


import uvicorn
from fastapi import FastAPI, Path, Query, HTTPException
#from rasterio.crs import CRS
from starlette.requests import Request
from starlette.responses import Response

#from rio_tiler.profiles import img_profiles
from rio_tiler.io import COGReader
from rasterio.io import MemoryFile
from rio_tiler.utils import mapzen_elevation_rgb
import json
import numpy

cog = COGReader("dem.vrt", maxzoom=18, minzoom=11, resampling_method="nearest")

coginfo = cog.info()
print(coginfo)
print(json.dumps({"bounds": {"minX": coginfo.bounds.left, "minZ": coginfo.bounds.bottom, "maxX": coginfo.bounds.right, "maxZ": coginfo.bounds.top}}, indent=4))

app = FastAPI(
    title="rio-tiler",
    description="A lightweight GeoTIFF tile server",
    docs_url=None,
    redoc_url=None
)

@app.get("/")
async def root():
    return {"message": "Tile server."}


@app.get(
    r"/{z}/{x}/{y}.tif",
    responses={
        200: {
            "content": {"image/tiff": {}}, "description": "Return an image.",
        }
    },
    #response_class=ImageResponse,
    description="Read COG and return a tile",
)
async def tile(
    z: int,
    x: int,
    y: int
):
    """Handle tile requests."""
    if z < cog.minzoom or z > cog.maxzoom:
        raise HTTPException(status_code=404, detail="Zoom level out of bounds.")
    if not cog.tile_exists(x, y, z):
        raise HTTPException(status_code=404, detail="Tile does not exist")
    img = cog.tile(x, y, z)
    count, height, width = img.data.shape
    output_profile = dict(
        driver="GTIFF",
        dtype=img.data.dtype,
        count=count,
        height=height,
        width=width,
        compress="DEFLATE",
        crs=img.crs,
        transform=img.transform
    )

    with MemoryFile() as memfile:
        with memfile.open(**output_profile) as dst:
            dst.write(img.data, indexes=list(range(1, count + 1)))
            dst.nodata = cog.nodata
        return Response(memfile.read(), media_type="image/tiff")

@app.get(
    r"/{z}/{x}/{y}.png",
    responses={
        200: {
            "content": {"image/png": {}}, "description": "Return an image.",
        }
    },
    #response_class=ImageResponse,
    description="Read COG and return a tile",
)
async def tilepng(
    z: int,
    x: int,
    y: int
):
    """Handle tile requests."""
    if z < cog.minzoom or z > cog.maxzoom:
        raise HTTPException(status_code=404, detail="Zoom level out of bounds.")
    if not cog.tile_exists(x, y, z):
        raise HTTPException(status_code=404, detail="Tile does not exist")
    img = cog.tile(x, y, z)
    count, height, width = img.data.shape
    output_profile = dict(
        driver="PNG",
        dtype='uint8',
        count=3,
        height=height,
        width=width,
        crs=img.crs,
        transform=img.transform
    )

    rgbdata = mapzen_elevation_rgb(img.data[0])

    with MemoryFile() as memfile:
        with memfile.open(**output_profile) as dst:
            dst.write(rgbdata)
        return Response(memfile.read(), media_type="image/png")



@app.get("/tilejson.json", responses={200: {"description": "Return a tilejson"}})
async def tilejson(
    request: Request,
):
    """Return TileJSON document for a COG."""

    return {
        "bounds": cog.geographic_bounds,
        "minzoom": cog.minzoom,
        "maxzoom": cog.maxzoom
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=3610, log_level="info")

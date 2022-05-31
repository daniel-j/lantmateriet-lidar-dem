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


#import uvicorn
from fastapi import FastAPI, Path, Query, HTTPException
#from rasterio.crs import CRS
from starlette.requests import Request
from starlette.responses import Response

#from rio_tiler.profiles import img_profiles
from rio_tiler.io import COGReader
from rasterio.io import MemoryFile


cog = COGReader("dem.vrt", maxzoom=17, resampling_method="nearest")

print(cog.info())

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
    print(img.bounds)
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
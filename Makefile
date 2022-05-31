
LIDARFILES = $(shell find input -maxdepth 1 -name '*.laz' | sort)
DEMFILES = $(patsubst input/%.laz,output/dem_%.tif,$(LIDARFILES))


.PHONY: dem.vrt server
.PRECIOUS: output/dem_%.tif
default: dem.vrt

output/dem_%.tif: input/%.laz
	@mkdir -p output
	time ./process.py "$<" "$@" 500
#	@IFS='_' read -r -a arr <<< "$<"; time pdal pipeline ./pipeline_raster.json --readers.las.filename="$<" --writers.raster.filename="$@.tmp" --filters.faceraster.origin_y="$$(($${arr[1]}*100))" --filters.faceraster.origin_x="$$(($${arr[2]}*100))"
#	@gdal_fillnodata.py -md 2500 "$@.tmp" "$@" -co COMPRESS=ZSTD
#	@gdal_translate -srcwin 10 10 2500 2500 merged1f.tif merged1fc.tif -co COMPRESS=ZSTD
#	@mv "$@.tmp" "$@"
#	@rm -f "$@.tmp"
	@echo "Finished writing $@"

dem.vrt: $(DEMFILES)
	@rm -f dem.vrt && gdalbuildvrt -overwrite dem.vrt output/dem_*.tif

server: dem.vrt
	uvicorn tiler:app --reload --host 0.0.0.0 --port 3610

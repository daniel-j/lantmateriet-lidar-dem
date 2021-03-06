
SHELL = bash
INPUTDIR = input
OUTPUTDIR = output
LIDARFILES = $(shell find $(INPUTDIR) -maxdepth 3 -type f -name '*.laz' | sort)
DEMFILES = $(patsubst $(INPUTDIR)/%.laz,$(OUTPUTDIR)/%.tif,$(LIDARFILES))
OUTDIRS = $(shell find $(OUTPUTDIR) -maxdepth 2 -mindepth 2 -type d | sort)
VRTFILES = $(patsubst $(OUTPUTDIR)/%,$(OUTPUTDIR)/%.vrt,$(OUTDIRS))

.PHONY: server mount unmount dems cog
.PRECIOUS: $(OUTPUTDIR)/%.tif
default: $(DEMFILES) dem.vrt

$(OUTPUTDIR)/%.tif: $(INPUTDIR)/%.laz
	@echo "Processing $<"
	@mkdir -pv $(dir $@)
	@time ./process.py "$<" "$@" 500
	@rio cogeo create --use-cog-driver --overview-level 8 "$@.tmp.tif" "$@"
	@rm -fv "$@.tmp.tif" "$@.laz"
#	@IFS='_' read -r -a arr <<< "$<"; time pdal pipeline ./pipeline_raster.json --readers.las.filename="$<" --writers.raster.filename="$@.tmp" --filters.faceraster.origin_y="$$(($${arr[1]}*100))" --filters.faceraster.origin_x="$$(($${arr[2]}*100))"
#	@gdal_fillnodata.py -md 2500 "$@.tmp" "$@" -co COMPRESS=ZSTD
#	@gdal_translate -srcwin 10 10 2500 2500 merged1f.tif merged1fc.tif -co COMPRESS=ZSTD
#	@mv "$@.tmp" "$@"
#	@rm -f "$@.tmp"
	@echo "Finished writing $@"

$(OUTPUTDIR)/%.vrt: $(OUTPUTDIR)/%/*25.tif
	@echo Generating "$@"
	@rm -f "$@" && gdalbuildvrt -overwrite "$@" $^

dem.vrt: $(VRTFILES)
	@rm -f dem.vrt && gdalbuildvrt -overwrite dem.vrt $^

server:
	uvicorn tiler:app --reload --host 0.0.0.0 --port 3610

mount:
	@gio mount ftp://download-opendata.lantmateriet.se < ftp.passwd
	@ln -svf "/run/user/$$(id -u)/gvfs/ftp:host=download-opendata.lantmateriet.se/Laserdata_Skog" inputremote
unmount:
	@gio mount -u "/run/user/$$(id -u)/gvfs/ftp:host=download-opendata.lantmateriet.se"
	@rm -f inputremote

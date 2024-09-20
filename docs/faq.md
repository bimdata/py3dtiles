# FAQ and Troubleshooting

Here are some common questions and issues. Please feel free to open an issue if it doesn't solve your problem.

## My tileset position is incorrect

This is a common issue with all GIS software and data. Let's go through some common things to check.

### Check your input file CRS

Does your input file headers or metadata includes such information? For pointclouds, you can check with `pdal info --summary`. For other type of data, please use relevant tools. Qgis is often very useful for this.

If it does, is this information correct?

Tools like QGis or ["Quelle est cette projection?" website](https://app.dogeo.fr/Projection/) (in French) can be very useful to check if the information is correct, or simply to find the correct CRS if the information is simply not there.

### Check your output CRS

This part depends of the use of your converted tileset:


- Cesium scene is in EPSG:4978, you need to pass`--srs_out 4978` in your `py3dtiles convert` invocation, or use `crs_out=4978` in your API usage
- for other viewers supporting several scene CRS, like giro3d, you should use the scene CRS.

### Does your data use traditional coordinates ordering instead of the CRS definition?

GDAL documentation has a [really good explanation about this issue](https://gdal.org/en/latest/tutorials/osr_api_tut.html#crs-and-axis-order).

In summary, CRS definitions includes an axis ordering. For instance [`EPSG:4326` axis order is defined as latitude-longitude](https://epsg.io/4326). [`EPSG:2326`](https://epsg.io/2326) is defined as northing - easting. However, the traditional GIS order still used by at least qgis, postgis and pdal for instance is "longitude - latitude", or "easting - northing", whatever the CRS definition mandates. Some data also uses this convention.

Py3dtiles has made the choice to use the [same default as proj itself](https://proj.org/en/9.5/faq.html#why-is-the-axis-ordering-in-proj-not-consistent): strictly honour the CRS definition order by default. We do offer an escape hatch to support the other use case (like pyproj). If this is your case, please use `--pyproj-always-xy` (cli usage) or `pyproj_always_xy=True` (API usage).

Please also see [the FAQ part of pyproj about axis order](https://pyproj4.github.io/pyproj/stable/gotchas.html#axis-order-changes-in-proj-6).

### I've checked everything, but my data is still at the wrong position

Please [open an issue](https://gitlab.com/py3dtiles/py3dtiles/-/issues), including what you checked and the results so far.

import simplekml

from main import fetch_os_details

kml = simplekml.Kml()
kml.newpoint(name="OS TEST", coords=[(-47.962979, -18.153650)])
kml.save("OS MAP.kml")
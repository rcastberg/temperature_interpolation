# temperature_interpolation
Interpolate temperatures based on a map


Point interpolate at floors.yaml, which show the walls and the thermometers:

```
Token: "ABCDEF...XYZ"
Step_size: 0.2
ha_url: "http://ha.local:8123/api/states/"
cpu_cores: 2
Floors:
  Basement:
    thermometers:
      - name: Thermo1
        x: 1
        y: 2
        ha_entity: sensor.Thermo1
      - name: Thermo2
        x: 2
        y: 3
        ha_entity: sensor.Thermo2
    walls:
      - [[0,0], [4,0]]
      - [[4,0], [4,5]]
      - [[4,5], [0,5]]
      - [[0,5], [0,0]]
```

The docker images spins up a flask server on port 5000, request an image at :
http://ha.local:8123/Basement.jpg, where Basement is defined in floors

ha_url is the url of you home assitant instance
The image extension in the request URL is any that are supported by kaleido.
Step size is the resolution of your rendered image, the higher the resolution, the longer it will take to run.
Token is a long lived token found in http://ha.local/profile.
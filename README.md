# <b>Homeassistant Addon for Ukrainian Socket-Giant Lan Relay Board</b> </br>

**This Addon may work fine with another VKmodule relays if they have same API**

https://vkmodule.com.ua/Ethernet/SocketGiant_ua.html </br>

Also here you can find official software and documentation for it : </br>
https://github.com/mamontuka/socket-giant-ha/tree/main/official_software_and_documentation

Instalation : </br>
1 - Add this repository to addons (three dots) - https://github.com/mamontuka/socket-giant-ha </br>
2 - Install this addon </br>
3 - In addon setings setup Lan Relay IP, port, login, password, MQTT settings </br>
4 - Take example below, ajust for self </br>

Homeassistant entities card configuration example :  https://github.com/mamontuka/socket-giant-ha/tree/main/entities_card_example </br>

**UPDATE 1.1 - added multiboard/relay modules support, tunable relay count (for device models with less relays), switches inverting - normal connected/normal disconected** </br>
 </br>
**UPDATE 1.2 - added functionality for relay work logic as short time TRIGGER, instead two position switch, config logic same like have relay mode invertation** </br>
 </br>
Addon config explanation : </br>

    # Board 1 ID for prefix to entities unique ID, like "socket_giant_1_rl_5"
    - device_id: socket_giant_1
    # You have this board IRL ? true - yes, false - SKIP this board
      enabled: true
    # Changeable board name in MQTT anouncement
      friendly_name: Socket Giant 1
    # Board 1 IP address
      relay_ip: 192.168.0.191
    # Boart port, default 80, but can be changed if you use board behind NAT
      relay_port: 80
    # Default login and password for board 1
      relay_login: admin
      relay_password: admin
    # How much relays this board have ? Usable for another VKmodule relay devices with same API
      relay_count: 16
    # Default relays state - printed here relays numbers have NC (normaly connected) wiring, not printed - normaly disconnected.
    # Thats inverting switches in Homeassistant
      inverted_relays:
        - 0
        - 1
        - 2
        - 3
        - 4
        - 5
        - 6
        - 7
        - 8
    # relay numbers what act like trigger, instead two position switch
      triggers:
        - 14
        - 15
    # Board 2 ID for prefix to entities unique ID, like "socket_giant_2_rl_1"
      - device_id: socket_giant_2
    # You have this board IRL ? true - yes, false - SKIP this board
      enabled: false
    # Changeable board name in MQTT anouncement
      friendly_name: Socket Giant 2
    # Board 2 IP address
      relay_ip: 192.168.0.192
    # Boart port, default 80, but can be changed if you use board behind NAT
      relay_port: 80
    # Default login and password for board 2
      relay_login: admin
      relay_password: admin
    # How much relays this board have ? Usable for another VKmodule relay devices with same API
      relay_count: 8
    # Default relays state - printed here relays numbers have NC (normaly connected) wiring, not printed - normaly disconnected.
    # Thats inverting switches in Homeassistant
      inverted_relays:
        - 3
        - 4
        - 5
    # relay numbers what act like trigger, instead two position switch
      triggers:
        - 1
        - 2
    # More VKmodules boards/relay modules with same API can be added below by copying and ajusting 
    # example configurations

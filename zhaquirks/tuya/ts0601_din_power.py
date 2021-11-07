"""Tuya Din Power Meter."""
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from zigpy.profiles import zha
from zigpy.zcl.clusters.general import AnalogInput, Basic, Groups, Ota, PowerConfiguration, Scenes, Time 
from zigpy.zcl import foundation
import zigpy.types as t
from zigpy.quirks import CustomCluster, CustomDevice 
from zhaquirks import Bus, LocalDataCluster
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement
from zigpy.zcl.clusters.smartenergy import Metering

from homeassistant.const import (
    ELECTRIC_POTENTIAL_VOLT,
    ELECTRIC_CURRENT_AMPERE,
)


from zhaquirks import PowerConfigurationCluster

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.tuya import (
    TuyaManufClusterAttributes,
    TuyaSwitch,
    TuyaManufacturerClusterOnOff,
    TuyaOnOff,
)

TUYA_TOTAL_ENERGY_ATTR = 0x0211
TUYA_CURRENT_ATTR = 0x0212
TUYA_POWER_ATTR = 0x0213
TUYA_VOLTAGE_ATTR = 0x0214
TUYA_DIN_SWITCH_ATTR = 0x0101

SWITCH_EVENT = "switch_event"

class TuyaManufClusterDinPower(TuyaManufClusterAttributes):
    """Manufacturer Specific Cluster of the Tuya Power Meter device."""

    manufacturer_attributes = {
        TUYA_TOTAL_ENERGY_ATTR: ('energy', t.uint16_t),
        TUYA_CURRENT_ATTR: ('current', t.int16s),
        TUYA_POWER_ATTR: ('power', t.uint16_t),
        TUYA_VOLTAGE_ATTR: ('voltage', t.uint16_t),
        TUYA_DIN_SWITCH_ATTR: ('switch', t.uint8_t)
    }

    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)
        if attrid == TUYA_TOTAL_ENERGY_ATTR:
            self.endpoint.device.energy_bus.listener_event(
                "energy_reported", value / 100
            )
        elif attrid == TUYA_CURRENT_ATTR:
            self.endpoint.device.electrical_bus.listener_event(
                "current_reported", value / 1000
            )
        elif attrid == TUYA_POWER_ATTR:
            self.endpoint.device.electrical_bus.listener_event(
                "power_reported", value / 10
            )
        elif attrid == TUYA_VOLTAGE_ATTR:
            self.endpoint.device.electrical_bus.listener_event(
                "voltage_reported", value / 10
            )
        elif attrid == TUYA_DIN_SWITCH_ATTR:
            self.endpoint.device.switch_bus.listener_event(
                "switch_event", attrid, value
            )

class TuyaPowerMeasurement(LocalDataCluster,ElectricalMeasurement):
   
    cluster_id = ElectricalMeasurement.cluster_id    
    POWER_ID = 0x050B
    VOLTAGE_ID = 0x0505
    CURRENT_ID = 0x0508

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)

        self.endpoint.device.electrical_bus.add_listener(self)


    def voltage_reported(self,value):
        """Voltage reported."""
        self._update_attribute(self.VOLTAGE_ID, value)
    def power_reported(self,value):
        """Power reported."""
        self._update_attribute(self.POWER_ID, value )
    def current_reported(self,value):
        """Current reported."""
        self._update_attribute(self.CURRENT_ID, value)            

class TuyaElectricalMeasurement(LocalDataCluster,Metering):

    cluster_id = Metering.cluster_id
    CURRENT_ID = 0x0000
    POWER_WATT = 0x0000

    """Setting unit of measurement."""
    _CONSTANT_ATTRIBUTES = {0x0300: POWER_WATT}

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.energy_bus.add_listener(self)

    def energy_reported(self,value):
        """Summation Energy reported."""
        self._update_attribute(self.CURRENT_ID, value)

class TuyaPowerMeter(TuyaSwitch):
    """Tuya power meter device."""

    def __init__(self, *args, **kwargs):
        """Init device."""
        self.switch_bus = Bus()
        self.energy_bus = Bus()
        self.electrical_bus = Bus()
        super().__init__(*args, **kwargs)


    signature = {
        # "node_descriptor": "<NodeDescriptor byte1=1 byte2=64 mac_capability_flags=142 manufacturer_code=4098
        #                       maximum_buffer_size=82 maximum_incoming_transfer_size=82 server_mask=11264
        #                       maximum_outgoing_transfer_size=82 descriptor_capability_field=0>",
        # device_version=1
        # input_clusters=[0x0000, 0x0004, 0x0005, 0xef00]
        # output_clusters=[0x000a, 0x0019]
        
        MODELS_INFO: [
            ("_TZE200_byzdayie", "TS0601"),
        ],
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=1 profile=260 device_type=51 
            # device_version=1 
            # input_clusters=[0, 4, 5, 61184] 
            # output_clusters=[10, 25]>
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaManufClusterAttributes.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaManufClusterDinPower,
                    TuyaPowerMeasurement,
                    TuyaElectricalMeasurement,
                    TuyaOnOff,
                 ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            }
        }
    }



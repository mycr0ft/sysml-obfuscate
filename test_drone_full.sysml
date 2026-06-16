package DroneModel {
    private import ISQ::*;
    private import SI::*;

    item def Thrust;
    item def VideoStream;
    item def OrientationData;
    item def MotorCommand;

    port def PowerOutPort  { out current : ElectricChargeValue; }
    port def PowerInPort   { in current : ElectricChargeValue; }
    port def CommandOutPort { out cmd : MotorCommand; }
    port def CommandInPort  { in cmd : MotorCommand; }
    port def VideoOutPort   { out video : VideoStream; }

    part def Battery {
        port supply : PowerOutPort;
        attribute capacity : ElectricChargeValue = 5000 [mAh];
    }

    part def Motor {
        port power : PowerInPort;
        port cmd   : CommandInPort;
        out item thrust : Thrust;
    }

    part def Camera {
        port power : PowerInPort;
        port video : VideoOutPort;
    }

    part def FlightController {
        port power     : PowerInPort;
        port motorCmd  : CommandOutPort [4];
        port videoIn   : VideoOutPort;

        perform action stabilize {
            in  attitude : OrientationData;
            in  imagery  : VideoStream;
            out commands : MotorCommand [4];
        }
    }

    part def Drone {
        attribute endurance : TimeValue;

        part battery    : Battery;
        part motors     : Motor [4];
        part camera     : Camera;
        part controller : FlightController;

        connect battery.supply to controller.power;
        connect camera.video to controller.videoIn;

        exhibit state operational {
            state idle;
            state flying;
            state landing;

            transition takeoff first idle accept signal: TakeoffCmd then flying;
            transition land    first flying  accept signal: LandCmd    then landing;
            transition done    first landing then idle;
        }
    }

    requirement def MinimumEndurance {
        doc /* The drone shall fly for at least 20 minutes on a full charge. */
        subject d : Drone;
        attribute minimum : TimeValue = 20 [min];
        require constraint { d.endurance >= minimum }
    }

    part myDrone : Drone {
        attribute :>> endurance = 25 [min];
        satisfy MinimumEndurance;
    }
}

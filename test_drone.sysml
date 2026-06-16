package DroneModel {
    private import ISQ::*;
    private import SI::*;

    part def Battery {
        doc /* A rechargeable power source for the drone. */
        attribute capacity : ElectricChargeValue;
    }

    part def Motor {
        doc /* An electric motor that drives a propeller. */
    }

    part def Camera {
        doc /* Captures video for the flight controller. */
    }

    part def Drone {
        doc /* A quadcopter unmanned aerial vehicle. */
        attribute endurance : TimeValue;

        part battery : Battery;
        part motors : Motor [4];
        part camera : Camera;
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

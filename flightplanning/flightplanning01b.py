import numpy  as np
import random as rnd
import datetime as dt


"""
reload(H); 
pp(H.Complete)
len(H.Complete)

demo of shallow copying:
sum([len(F) for F in H.Complete])
len(set([id(f) for F in H.Complete for f in F]))

Leg("Air",  "SAW", "AYT", dt.time.fromisoformat("13:45:00"), dt.time.fromisoformat("15:05:00"))
Leg("Idle", "AYT", "AYT", dt.time.fromisoformat("15:05:00"), dt.time.fromisoformat("15:40:00"))
Leg("Air",  "AYT", "SAW", dt.time.fromisoformat("15:40:00"), dt.time.fromisoformat("17:00:00"))

how to generate a random leg from L.dest: 
rnd.choice(Destinations[L.orig])

TODO Code:
-prune all plans from Complete that do not end at the Hub
-place functionality of this module into functions

TODO Research:
-find the term for "plane task assignment list" (list of flight legs & idles)
-find the term for common term for a flight leg or an idle assigment (could be apron, fuel, TAT, gate, ...)
-read the network structure from a file
"""



class Arc:
    def __init__(self, distance=None, duration=None):
        self.distance = distance  # distance (km)   int
        self.duration = duration  # duration (min)  timedelta

    def __repr__(self) -> str:
        return f"Arc({self.distance:4d}, {self.duration.total_seconds()/60:3.0f})"


class Leg:
    def __init__(self, type=None, orig=None, dest=None, dept=None, arrv=None):
        self.type = type  # leg type ("Air", "Idle")  str
        self.orig = orig  # origin (from) airport     str
        self.dest = dest  # destination (to) airport  str
        self.dept = dept  # departure time            datetime.datetime
        self.arrv = arrv  # arrival time              datetime.datetime

    def __repr__(self) -> str:
        # f'{x:%Y-%m-%d %H:%M}'
        return ( f"{self.type:4s} {self.orig:3s}-" + 
                (f"{self.dest:3s} " if self.dest else "--- ") + 
                 f"{self.dept:%H:%M}-{self.arrv:%H:%M}")


def print_plan(title, P):
    L1 = (f"{title}: " + 
          "".join([(f"{x.orig:>5s}" + ("-" if x.type=="Air" else ".")) for x in P]) + 
          f"{P[-1].dest:>5s}" + ("-" if P[-1].type=="Air" else "."))
    L2 = (" "*len(title) + "  " + 
          "".join([f" {x.dept:%H:%M}" for x in P]) + 
          f" {P[-1].arrv:%H:%M}")
    print(L1)
    print(L2)



Airports = {
    "SAW" : "İstanbul Sabiha Gökçen", 
    "ESB" : "Ankara Esenboğa", 
    "AYT" : "Antalya",
}

Network = { A:{} for A in Airports.keys() }
Network["SAW"]["ESB"] = Arc(323, dt.timedelta(minutes=60))
Network["SAW"]["AYT"] = Arc(652, dt.timedelta(minutes=75))
Network["ESB"]["AYT"] = Arc(406, dt.timedelta(minutes=65))


"""
make the network symmetric
(assuming symmetry in flight times)
in the following loop, following line: 
    Network[to_city][from_city] = arc
    does not create distinct objects but rather 
    will create references to the existing objects
OTOH following line:
    Network[to_city][from_city] = Arc(arc)
    will create a new Arc() object for symmetric Arcs
"""
for from_city, destinations in Network.items():
    for to_city, a in destinations.items(): 
        Network[to_city][from_city] = Arc(a.distance, a.duration)

"""
we may need to limit (or prioritize) which airports are allowed 
to be the next leg from each airport: create a list of all possible 
(or allowed) destinations from each airport
this list (indexable) can be used to select random destinations 
with random.choice()
"""
Destinations = {}
for from_city in Network.keys():
    Destinations[from_city] = list(set(Network[from_city].keys()) - set(from_city))

Duration_Mod = 1
for from_city, destinations in Network.items():
    for to_city, arc in destinations.items():
        arc.duration *= Duration_Mod


"""
Root of all flight plans is the Hub
Create all possible flight plans that: 
  - start and end at the Hub and
  - fit into the time window: [Start_Time, End_Time]
Start and End Time may not be on the same day, e.g. 06:00 - 00:40(next day)
"""
Flight_Plan_Hub = "SAW"
Flight_Plan_Start_Time = dt.datetime(year=2000, month=1, day=1, hour=6, minute=0)
Flight_Plan_End_Time = Flight_Plan_Start_Time + dt.timedelta(hours=16, minutes=0)
Turnaround_Time = dt.timedelta(minutes=30)

# remind ourselves the data is modified
print(f"Duration Modifier = {Duration_Mod}")
print(f"TAT = {Turnaround_Time}")


"""
Algorithm
  Flight Plan = list of consecutive Flight Legs

  initialization:
    list of   complete flight plans = Complete = []
    list of incomplete flight plans = Incomplete = [all possible flight plans with 1 Air leg 
                                                    starting at the Hub at Start_Time]

  iteration: 
    for each flight plan X in Incomplete
      either: remove the selected incomplete flight plan X from Incomplete
              append all allowable (permissible) flight legs to X
              permissible = if landing time is before the End_Time
              add these extended plans as incomplete plans to Incomplete
          or: if no allowable flight legs can be added to X 
              append X to Complete

  clean up:
    for each flight plan X in Complete
      remove all flight legs from the end of X that are not the Hub
"""

Incomplete, Complete = [], []
for dst in Destinations[Flight_Plan_Hub]:
    F = Leg(type="Air")
    F.orig = Flight_Plan_Hub
    F.dest = dst
    F.dept = Flight_Plan_Start_Time
    F.arrv = Flight_Plan_Start_Time + Network[F.orig][F.dest].duration
    I = Leg(type="Idle", orig=dst, dest=dst)
    I.dept = F.arrv
    I.arrv = F.arrv + Turnaround_Time
    Incomplete.append([F, I])


while Incomplete:
    X = Incomplete.pop()
    fr = X[-1].dest
    # if it is possible to add 1 flight leg to X 
    # that arrives its destination before End Time
    # then add that alternative to Incomplete and keep X deleted
    # otherwise (if none can be found) append X to complete
    num_ex = 0
    for to in Destinations[fr]:
        # generate and evaluate alternatives
        F = Leg(type="Air", 
                orig=fr, 
                dest=to, 
                dept=X[-1].arrv,
                arrv=X[-1].arrv + Network[fr][to].duration)
        if F.arrv <= Flight_Plan_End_Time:
            num_ex += 1
            I = Leg(type="Idle", 
                    orig=F.dest, 
                    dest=F.dest, 
                    dept=F.arrv,
                    arrv=min(F.arrv + Turnaround_Time, Flight_Plan_End_Time))
            # note that the following is a shallow copy
            # we keep on building plane assignments on top of earlier segments
            Incomplete.append(X + [F, I])
            

    if num_ex == 0:
        Complete.append(X)
    else:
        # do nothing
        # X is discarded as it gave birth to at least one child
        pass


for i,X in enumerate(Complete):
    print_plan(f"{i+1:03d}", X)
    print()



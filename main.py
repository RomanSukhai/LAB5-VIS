from mesa import Agent, Model
from mesa.time import RandomActivation
from mesa.space import MultiGrid
from mesa.datacollection import DataCollector
from mesa.visualization.modules import CanvasGrid, ChartModule
from mesa.visualization.ModularVisualization import ModularServer
from mesa.visualization.UserParam import Slider
import random


class CarAgent(Agent):
    def __init__(self, unique_id, model, car_type):
        super().__init__(unique_id, model)
        self.car_type = car_type 
        self.direction = self.random_direction()

    def random_direction(self):
        """Вибирає випадковий напрямок руху."""
        return (random.choice([-1, 0, 1]), random.choice([-1, 0, 1]))

    def step(self):

        new_x = self.pos[0] + self.direction[0]
        new_y = self.pos[1] + self.direction[1]

        if new_x < 0 or new_x >= self.model.grid.width or new_y < 0 or new_y >= self.model.grid.height:
            self.direction = self.random_direction()
            return

        new_position = (new_x, new_y)
        other_agents = self.model.grid.get_cell_list_contents([new_position])

        if len(other_agents) > 0:
            aggressive_present = any(agent.car_type == 2 for agent in other_agents)
            if aggressive_present:
                for agent in other_agents:
                    if agent in self.model.schedule.agents:
                        self.model.schedule.remove(agent)
                        self.model.grid.remove_agent(agent)
                if self in self.model.schedule.agents:
                    self.model.schedule.remove(self)
                    self.model.grid.remove_agent(self)
                self.model.steps_without_collisions = 0
            else:
                if self.car_type == 1:
                    self.direction = (random.choice([-1, 1]), 0) if random.choice([True, False]) else (
                    0, random.choice([-1, 1]))
        else:
            self.model.grid.move_agent(self, new_position)


class TrafficModel(Model):
    def __init__(self, N1, N2, width, height, speed):
        self.grid = MultiGrid(width, height, False)
        self.schedule = RandomActivation(self)
        self.speed = speed
        self.steps_without_collisions = 0
        self.datacollector = DataCollector(
            {
                "Кількість поступливих машин": lambda m: sum(
                    1 for agent in m.schedule.agents if isinstance(agent, CarAgent) and agent.car_type == 1),
                "Кількість агресивних машин": lambda m: sum(
                    1 for agent in m.schedule.agents if isinstance(agent, CarAgent) and agent.car_type == 2)
            }
        )
        for i in range(N1):
            self.add_agent(i, car_type=1)
        for i in range(N1, N1 + N2):
            self.add_agent(i, car_type=2)

    def add_agent(self, agent_id, car_type):
        """Додає машину з унікальним ідентифікатором та типом."""
        car = CarAgent(agent_id, self, car_type)
        self.schedule.add(car)
        x = self.random.randrange(self.grid.width)
        y = self.random.randrange(self.grid.height)
        self.grid.place_agent(car, (x, y))

    def step(self):
        self.datacollector.collect(self)
        for _ in range(self.speed):
            self.schedule.step()
        self.steps_without_collisions += 1
        if self.steps_without_collisions >= 5:
            count_type_1 = sum(
                1 for agent in self.schedule.agents if isinstance(agent, CarAgent) and agent.car_type == 1)
            count_type_2 = sum(
                1 for agent in self.schedule.agents if isinstance(agent, CarAgent) and agent.car_type == 2)
            if count_type_1 > count_type_2:
                new_car_type = 1
            else:
                new_car_type = 2
            new_id = max(agent.unique_id for agent in self.schedule.agents if isinstance(agent, CarAgent)) + 1
            self.add_agent(new_id, new_car_type)
            self.steps_without_collisions = 0

def agent_portrayal(agent):
    if isinstance(agent, CarAgent):
        color = "blue" if agent.car_type == 1 else "red"
        return {
            "Shape": "rect",
            "Color": color,
            "Filled": "true",
            "Layer": 0,
            "w": 0.8,
            "h": 0.8
        }


grid = CanvasGrid(agent_portrayal, 20, 20, 500, 500)
chart = ChartModule([
    {"Label": "Кількість поступливих машин", "Color": "blue"},
    {"Label": "Кількість агресивних машин", "Color": "red"}
])
server = ModularServer(
    TrafficModel,
    [grid, chart],
    "Модель дорожнього руху з двома типами машин",
    {
        "N1": Slider("Кількість початкових поступливих машин", 1, 1, 50, 1),
        "N2": Slider("Кількість початкових агресивних машин", 1, 1, 50, 1),
        "width": Slider("Ширина сітки", 10, 10, 50, 1),
        "height": Slider("Висота сітки", 10, 10, 50, 1),
        "speed": Slider("Швидкість машин (кроки за такт)", 1, 1, 10, 1)
    }
)

server.port = 8521
server.launch()

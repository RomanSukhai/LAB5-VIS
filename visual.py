from mesa import Agent, Model
from mesa.time import RandomActivation
from mesa.space import MultiGrid
from mesa.datacollection import DataCollector
import matplotlib.pyplot as plt
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
        # Перевірка, чи агент має позицію на сітці
        if self.pos is None:
            return

        # Розраховуємо нову позицію
        new_x = self.pos[0] + self.direction[0]
        new_y = self.pos[1] + self.direction[1]

        # Якщо машина досягає межі сітки, вона змінює напрямок
        if new_x < 0 or new_x >= self.model.grid.width or new_y < 0 or new_y >= self.model.grid.height:
            self.direction = self.random_direction()
            return

        new_position = (new_x, new_y)
        other_agents = self.model.grid.get_cell_list_contents([new_position])

        if len(other_agents) > 0:
            # Перевірка на наявність агресивних машин серед інших агентів
            aggressive_present = any(agent.car_type == 2 for agent in other_agents)
            if aggressive_present:
                # Якщо є агресивний водій, всі машини в клітинці стикаються і видаляються
                for agent in other_agents:
                    if agent in self.model.schedule.agents:
                        self.model.schedule.remove(agent)
                        self.model.grid.remove_agent(agent)
                if self in self.model.schedule.agents:
                    self.model.schedule.remove(self)
                    self.model.grid.remove_agent(self)
                self.model.steps_without_collisions = 0
            else:
                # Якщо всі машини в позиції поступливі, змінюємо напрямок для уникнення зіткнення
                if self.car_type == 1:
                    self.direction = (random.choice([-1, 1]), 0) if random.choice([True, False]) else (
                    0, random.choice([-1, 1]))
        else:
            # Рух агента, якщо немає інших машин
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

        # Додаємо початкові машини
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

        # Додаємо нову машину, якщо пройшло 5 кроків без зіткнень
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

    def visualize_results(self):
        """Візуалізація результатів після завершення моделювання."""
        data = self.datacollector.get_model_vars_dataframe()
        plt.figure(figsize=(10, 5))
        plt.plot(data["Кількість поступливих машин"], label="Кількість поступливих машин", color="blue")
        plt.plot(data["Кількість агресивних машин"], label="Кількість агресивних машин", color="red")
        plt.xlabel("Кроки")
        plt.ylabel("Кількість машин")
        plt.title("Динаміка кількості машин кожного типу")
        plt.legend()
        plt.show()


model = TrafficModel(N1=10, N2=100, width=20, height=20, speed=1)
for _ in range(100):
    model.step()
model.visualize_results()

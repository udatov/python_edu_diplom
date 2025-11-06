from abc import ABC, abstractmethod
from collections.abc import Callable
from enum import StrEnum
import time
from typing import Any, Dict, List
import pandas as pd
import matplotlib.pyplot as plt
from pydantic import BaseModel, Field, computed_field
from common.src.theatre.db.base import DqmLangStatementDB

DbQueryMethod = Callable[[DqmLangStatementDB, str], Any]


class TimeOperationMeasure(ABC):

    @abstractmethod
    async def apply_operation(self, operation: 'BenchmarkOperationResult'):
        pass

    async def measure_op(self, operation: 'BenchmarkOperationResult') -> float:
        start_tm = time.perf_counter()
        await self.apply_operation(operation=operation)
        return time.perf_counter() - start_tm


class BaseDbBenchmark(TimeOperationMeasure, ABC):

    @classmethod
    def combine_operation_result(
        cls, left: List['BenchmarkOperationResult'], right: List['BenchmarkOperationResult']
    ) -> List[Dict[str, Any]]:
        if len(left) != len(right):
            raise ValueError()

        i = 0
        results: List[Dict[str, Any]] = []
        while i < len(left):
            if left[i].operation_name != right[i].operation_name:
                raise ValueError()

            results.append(
                {
                    'op_name': left[i].operation_name,
                    f'{left[i].provider_title}_min': left[i].min,
                    f'{left[i].provider_title}_max': left[i].max,
                    f'{left[i].provider_title}_avg': left[i].avg,
                    f'{right[i].provider_title}_min': left[i].min,
                    f'{right[i].provider_title}_max': right[i].max,
                    f'{right[i].provider_title}_avg': right[i].avg,
                }
            )
            i += 1

        return results

    @classmethod
    def show_results(
        cls,
        results: List[Dict[str, Any]],
        l_provider: str = 'PostgreSQL',
        r_provider: str = 'Mongodb',
        fname: str = None,
    ):
        """Display and visualize results"""
        df = pd.DataFrame(results)
        print(df)

        # Plot comparison
        fig, ax = plt.subplots(figsize=(12, 6))
        width = 0.35
        x = range(len(df))

        ax.bar(x, df[f'{l_provider}_avg'], width, label=l_provider)
        ax.bar([p + width for p in x], df[f'{r_provider}_avg'], width, label=r_provider)

        ax.set_ylabel('Execution Time (seconds)')
        ax.set_title('Database Performance Comparison')
        ax.set_xticks([p + width / 2 for p in x])
        ax.set_xticklabels(df['op_name'])
        ax.legend()

        plt.xticks(rotation=45)
        plt.tight_layout()
        if fname:
            plt.savefig(fname=fname)
        plt.close(fig=fig)

    def __init__(self, operation_result_list: 'BenchmarkOperationResult'):
        super().__init__()
        self._operation_result_list = operation_result_list

    @abstractmethod
    async def create_db(self) -> None:
        pass

    @abstractmethod
    async def seed_db(self, count: int) -> None:
        pass

    @abstractmethod
    async def run(self) -> None:
        pass


class BenchmarkOperationResult(BaseModel):
    provider_title: str = Field(default="PostgreSQL")
    operation_name: StrEnum
    action_templ: str
    action_parameters: Dict[str, Any]
    iteration_count: int = Field(default=100)
    calc_time_list: List[float] = []
    min: float = Field(default=0.0)
    max: float = Field(default=0.0)
    avg: float = Field(default=0.0)

    @computed_field(return_type=str)
    def compiled_query(self):
        return self.action_templ.format(**self.action_parameters)

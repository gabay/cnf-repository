import glob
import os
import re
import subprocess
import sys
import time
import multiprocessing as mp

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATS_PATH = os.path.join(BASE_DIR, 'stats.txt')
WORKERS = mp.cpu_count() // 4

class Stats:
    """
    Stats file consists of three tab-separated fields:
    runtime    result(SAT/UNSAT/TIMEOUT_N)    path
    """
    def __init__(self, stats):
        self.stats = stats

    @classmethod
    def load(cls, path):
        stats = {}
        if os.path.exists(path):
            with open(path) as inp:
                for line in filter(None, map(str.strip, inp)):
                    runtime_str, result, problem_path = line.split('\t', 2)
                    stats[problem_path] = (float(runtime_str), result)
        return cls(stats)

    def save(self, path):
        with open(path, 'w') as out:
            for problem_path in sorted(self.stats, key=lambda path: self.stats[path][0]):
                runtime, result = self.stats[problem_path]
                out.write(f'{runtime:.3f}\t{result}\t{problem_path}\n')

    def get(self, problem_path):
        return self.stats.get(problem_path, (float('inf'), 'TIMEOUT_0'))

    def set(self, problem_path, runtime, result):
        self.stats[problem_path] = (runtime, result)

class Calculator:
    def __init__(self, stats, timeout):
        self.stats = stats
        self.timeout = timeout

    def calculate(self, problem_path):
        runtime, result = self.stats.get(problem_path)
        if not self.should_calculate(runtime, result):
            return problem_path, runtime, result

        try:
            proc = subprocess.run(['minisat', problem_path], capture_output=True, text=True, timeout=timeout)
            runtime = float(re.search(r'CPU time\s*: (\d+\.\d+) s', proc.stdout).group(1))
            result = proc.stdout.strip().splitlines()[-1]
        except subprocess.TimeoutExpired:
            runtime = float('inf')
            result = f'TIMEOUT_{timeout}'
        except AttributeError:
            import pdb; pdb.set_trace()
        return problem_path, runtime, result

    def should_calculate(self, runtime, result):
        if not result.startswith('TIMEOUT_'):
            return False

        tried_time = int(result.split('_')[1])
        return tried_time < self.timeout


def get_stats(problem_path, timeout):
    try:
        proc = subprocess.run(['minisat', problem_path], capture_output=True, text=True, timeout=timeout)
        runtime = float(re.search(r'CPU time\s*: (\d+\.\d+) s', proc.stdout).group(1))
        result = proc.stdout.strip().splitlines()[-1]
    except subprocess.TimeoutExpired:
        runtime = float('inf')
        result = f'TIMEOUT_{timeout}'
    except AttributeError:
        import pdb; pdb.set_trace()
    return runtime, result

def main(timeout):
    print('* Timeout:', timeout)
    stats = Stats.load(STATS_PATH)
    calculator = Calculator(stats, timeout)
    with mp.Pool(WORKERS) as pool:
        problems = sorted(glob.glob('cnf/**/*.cnf', recursive=True))
        for problem_path, runtime, result in pool.imap_unordered(calculator.calculate, problems):
            print(problem_path)
            print(f'  {runtime:.3f} {result}')
            if stats.get(problem_path)[0] != runtime:
                stats.set(problem_path, runtime, result)
                stats.save(STATS_PATH)

if __name__ == '__main__':
    timeout = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
    main(timeout)

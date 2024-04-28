import LLMP as L
import re
import time
import numpy as np
from sklearn.metrics import mean_squared_error
from sklearn.metrics import mean_absolute_error
import torch

class Evaluator:

    # Calculate mean squared error (MSE)
    def calculate_mse(gt, answers):
        gt_array = np.array(gt)
        answers_array = np.array(answers)

        return mean_squared_error(gt_array,answers_array)

    
    # Calculate midmean logistic absoulte error (MALE)
    def calculate_mlae(gt, answers):
        gt_array = np.array(gt)
        answers_array = np.array(answers)

        mlae = np.log2(mean_absolute_error(gt_array*100, answers_array*100) + .125)
        return mlae

    # Calculate mean
    def calculate_mean(answers):
        return np.mean(answers)

    # Calculate std
    def calculate_std(answers):
        return np.std(answers)

    @staticmethod
    def run(data, query, models):
        images = [d[0] for d in data]
        gt = [d[1] for d in data]
        results = {'gt': gt}

        for model_name in models:
            raw_answers = []
            parsed_answers = []
            forced_repetitions = 0
            times = []

            for image in images:
                torch.torch.cuda.empty_cache()
                FLAG = False
                start_time = time.time()

                while not FLAG:
                    answer = ""
                    match model_name:
                        case "LLaVA":
                            answer = L.LLaVA.query(query, image)
                        case "ChatGPT":
                            answer = L.ChatGPT.query(query, image)
                        case "CustomLLaVA":
                            answer = L.CustomLLaVA.query(query, image)

                    """
                    ranges = re.findall(r'\b(\d+)(?:-(\d+))?\b', answer)
                    if ranges:
                        ranges_numbers = [num for range_tuple in ranges for num in range_tuple if num]
                        ranges_numbers = [float(r) for r in ranges_numbers]"""
                        
                    pattern = r'(?<![\d\w*.-])\d+(?:\.\d+)?(?:-(?:\d+(?:\.\d+)?))?(?![\d\w*.-])'
                    matches = re.findall(pattern, answer)

                    if matches:
                        ranges_numbers = []
                        FLAG = 0
                        for match in matches:
                            if '-' in match:
                                FLAG = 1
                                ranges_numbers.extend(match.split('-'))
                                ranges_numbers = ranges_numbers[-2:]
                            else:
                                ranges_numbers.append(match)
                        if (FLAG == 0):
                            ranges_numbers = ranges_numbers[-1:]
                        ranges_numbers = [float(r) for r in ranges_numbers]
                        
                        raw_answers.append(answer)
                        parsed_answers.append(ranges_numbers)
                        FLAG = True
                        end_time = time.time()
                        times.append((end_time - start_time) * 1000)
                        if model_name == "ChatGPT":
                            time.sleep(5)  # Avoid hitting rate limits!
                    else:
                        forced_repetitions += 1
                        if model_name == "ChatGPT":
                            time.sleep(5)  # Avoid hitting rate limits!


            # Evaluation
            midpoints = None
            """
            if (len(parsed_answers[0])==1):
                midpoints = [item for sublist in parsed_answers for item in sublist]
            else:   
                midpoints = [(a+b)/2 for a, b in parsed_answers]"""
            midpoints = [(sum(sublist) / 2) if len(sublist) > 1 else sublist[0] for sublist in parsed_answers]

                
            mse = Evaluator.calculate_mse(gt, midpoints)
            mlae = Evaluator.calculate_mlae(gt, midpoints)
            mean = Evaluator.calculate_mean(midpoints)
            std = Evaluator.calculate_std(midpoints)

            results[model_name] = {
                'parameters': None, 
                'raw_answers': raw_answers,
                'parsed_answers': parsed_answers,
                'mean': mean,
                'std': std,
                'mse': mse, 
                'mlae': mlae, 
                'times': times,
                'forced_repetitions': forced_repetitions
            }

        return results

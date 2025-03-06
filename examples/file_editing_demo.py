#!/usr/bin/env python3
"""
Test file for demonstrating the file editing capabilities of the coding assistant.
"""

# This function has some bugs and could use improvements
def calculate_average(numbers):
    """
    Calculate the average of a list of numbers.
    
    Args:
        numbers: A list of numbers
        
    Returns:
        The average value
    """
    total = 0
    for num in numbers:
        total = total + num
    
    return total / len(numbers)


# This function should handle division by zero
def safe_divide(a, b):
    """
    Safely divide two numbers.
    
    Args:
        a: The numerator
        b: The denominator
        
    Returns:
        The result of a/b
    """
    return a / b


# This function is missing error handling
def read_configuration(filename):
    """
    Read a configuration file and return the settings.
    
    Args:
        filename: Path to the configuration file
        
    Returns:
        A dictionary of settings
    """
    config = {}
    with open(filename, 'r') as file:
        for line in file:
            if '=' in line:
                key, value = line.strip().split('=', 1)
                config[key.strip()] = value.strip()
    return config


if __name__ == "__main__":
    # Test calculate_average
    numbers = [1, 2, 3, 4, 5]
    print(f"Average of {numbers}: {calculate_average(numbers)}")
    
    # Test safe_divide
    print(f"10 / 2 = {safe_divide(10, 2)}")
    
    # This will cause an error - division by zero
    # print(f"10 / 0 = {safe_divide(10, 0)}")
    
    # This will cause an error - file not found
    # config = read_configuration("config.txt")
    # print(f"Configuration: {config}") 
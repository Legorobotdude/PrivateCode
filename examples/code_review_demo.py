#!/usr/bin/env python3
"""
Example file for testing the local LLM coding assistant.
"""

def fibonacci(n):
    """
    Compute the nth Fibonacci number.

    Args:
        n (int): The position in the Fibonacci sequence

    Returns:
        int: The nth Fibonacci number
    """
    if n <= 0:
        return 0
    elif n == 1:
        return 1
    else:
        return fibonacci(n-1) + fibonacci(n-2)

def is_prime(num):
    """Check if a number is prime."""
    if num <= 1:
        return False
    if num <= 3:
        return True
    if num % 2 == 0 or num % 3 == 0:
        return False
    i = 5
    while i * i <= num:
        if num % i == 0 or num % (i + 2) == 0:
            return False
        i += 6
    return True

# A function with room for improvement
def process_data(data):
    result = []
    for i in range(len(data)):
        if data[i] % 2 == 0:
            result.append(data[i] * 2)
        else:
            result.append(data[i] * 3)
    return result

if __name__ == "__main__":
    # Print first 10 Fibonacci numbers
    for i in range(10):
        print(f"Fibonacci({i}) = {fibonacci(i)}")

    # Test is_prime function
    test_numbers = [2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
    for num in test_numbers:
        print(f"{num} is prime: {is_prime(num)}")

    # Test process_data function
    sample_data = [1, 2, 3, 4, 5]
    processed = process_data(sample_data)
    print(f"Original data: {sample_data}")
    print(f"Processed data: {processed}")

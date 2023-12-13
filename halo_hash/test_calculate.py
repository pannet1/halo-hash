import pytest
from calculate import entry_quantity  # Replace 'your_module' with the actual name of the module containing your entry_quantity function

@pytest.mark.parametrize("ltp, kwargs, expected_quantity", [
    (210, {'symbol': 'JIOFIN', 'capital_in_thousand': '3', 'Risk per trade': '50', 'Margin required': '1', 'lot_size': '1', 'stop_loss': 10}, 8),  # Adjust the expected value based on your calculation logic
    # Add more test cases as needed
])
def test_entry_quantity_calculation(ltp, kwargs, expected_quantity):
    quantity = entry_quantity(ltp, **kwargs)

    # Assertions
    assert quantity == expected_quantity

if __name__ == "__main__":
    pytest.main()


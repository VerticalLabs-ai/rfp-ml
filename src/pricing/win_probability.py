class WinProbabilityModel:
    """
    Predicts win probability based on bid price relative to market benchmarks.
    """
    def __init__(self):
        pass

    def predict(self, bid_price: float, market_median: float, sensitivity: float = 2.5) -> float:
        """
        Calculate win probability for a given bid price against a market median.
        """
        if market_median <= 0:
            return 0.5
        price_ratio = bid_price / market_median

        # Linear approximation centered at 1.0 = 50%
        prob = 0.5 - (price_ratio - 1.0) * sensitivity

        return max(0.05, min(0.95, round(prob, 2)))

    def solve_for_price(self, target_prob: float, market_median: float, sensitivity: float = 2.5) -> float:
        """
        Calculate the maximum price that achieves the target win probability.
        """
        if market_median <= 0:
            return 0.0

        # Clamp target_prob to valid bounds (same as predict returns)
        target_prob = max(0.05, min(0.95, target_prob))

        # derived from: prob = 0.5 - (price/median - 1) * sensitivity
        optimal_price = market_median * (1 + (0.5 - target_prob) / sensitivity)

        return round(optimal_price, 2)

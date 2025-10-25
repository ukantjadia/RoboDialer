
"""
Script to create Stripe products and prices for pause subscriptions
This should be run once to set up the pause subscription products in Stripe
"""

import sys
import os
import stripe
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app

def create_pause_products():
    """Create pause subscription products and prices in Stripe"""
    app = create_app()
    
    with app.app_context():
        # Set up Stripe
        stripe.api_key = app.config['STRIPE_SECRET_KEY']
        
        try:
            # Create pause products and prices
            pause_products = [
                {'name': 'Subscription Pause - 1 Month', 'price': 1000, 'duration': 'pause_one_month'},   # $10.00
                {'name': 'Subscription Pause - 2 Months', 'price': 2000, 'duration': 'pause_two_month'}, # $20.00
                {'name': 'Subscription Pause - 3 Months', 'price': 3000, 'duration': 'pause_three_month'} # $30.00
            ]
            
            created_prices = {}
            
            for product_info in pause_products:
                # Create product
                product = stripe.Product.create(
                    name=product_info['name'],
                    description=f"Pause your subscription for a reduced rate of ${product_info['price']/100:.2f}",
                    metadata={
                        'type': 'pause_subscription',
                        'duration': product_info['duration']
                    }
                )
                
                print(f"Created product: {product.id} - {product.name}")
                
                # Create price
                price = stripe.Price.create(
                    product=product.id,
                    unit_amount=product_info['price'],
                    currency='usd',
                    metadata={
                        'type': 'pause_subscription',
                        'duration': product_info['duration']
                    }
                )
                
                created_prices[product_info['duration']] = price.id
                print(f"Created price: {price.id} - ${product_info['price']/100:.2f}")
            
            print("\n=== Update your config.py with these price IDs ===")
            for duration, price_id in created_prices.items():
                print(f"'{duration}': '{price_id}',")
            
            print("\n=== Pause products created successfully ===")
            
        except Exception as e:
            print(f"Error creating pause products: {str(e)}")

if __name__ == '__main__':
    create_pause_products()

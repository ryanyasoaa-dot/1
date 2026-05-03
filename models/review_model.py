"""
Review Model
Handles all database operations for product reviews using Supabase.
"""

from supabase import create_client
import os
from typing import Optional, List, Dict, Any


class ReviewModel:
    def __init__(self):
        self.supabase = create_client(
            os.getenv('SUPABASE_URL'),
            os.getenv('SUPABASE_SERVICE_ROLE_KEY')
        )

    def create_review(self, user_id: str, product_id: str, order_id: str, 
                      rating: int, comment: str = None, image_url: str = None) -> Dict[str, Any]:
        """Create a new review. Returns the created review or error."""
        data = {
            'user_id': user_id,
            'product_id': product_id,
            'order_id': order_id,
            'rating': rating,
        }
        if comment:
            data['comment'] = comment
        if image_url:
            data['image_url'] = image_url

        result = self.supabase.table('reviews').insert(data).execute()
        if result.data and len(result.data) > 0:
            return result.data[0]
        return {}

    def get_product_reviews(self, product_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get all reviews for a product with user info."""
        result = self.supabase.table('reviews').select('*'
        ).eq('product_id', product_id).order('created_at', desc=True).limit(limit).execute()
        
        reviews = []
        for row in (result.data or []):
            # Fetch user data separately to avoid FK relationship issues
            user = None
            if row.get('user_id'):
                user_result = self.supabase.table('users').select('id, first_name, last_name').eq('id', row['user_id']).single().execute()
                user = user_result.data if user_result.data else None
            
            user_name = f"{(user or {}).get('first_name', '')} {(user or {}).get('last_name', '')}".strip() or 'Anonymous'
            
            reviews.append({
                'id': row['id'],
                'user_id': row['user_id'],
                'product_id': row['product_id'],
                'order_id': row['order_id'],
                'rating': row['rating'],
                'comment': row.get('comment'),
                'image_url': row.get('image_url'),
                'created_at': row['created_at'],
                'updated_at': row.get('updated_at'),
                'user_name': user_name,
                'user_initial': (user_name[:1] or 'A').upper()
            })
        return reviews

    def get_user_reviews(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get all reviews by a user."""
        result = self.supabase.table('reviews').select('*'
        ).eq('user_id', user_id).order('created_at', desc=True).limit(limit).execute()
        
        reviews = []
        for row in (result.data or []):
            # Fetch product data separately to avoid FK relationship issues
            product = None
            if row.get('product_id'):
                product_result = self.supabase.table('products').select('id, name, seller_id').eq('id', row['product_id']).single().execute()
                product = product_result.data if product_result.data else None
            
            reviews.append({
                'id': row['id'],
                'user_id': row['user_id'],
                'product_id': row['product_id'],
                'order_id': row['order_id'],
                'rating': row['rating'],
                'comment': row.get('comment'),
                'image_url': row.get('image_url'),
                'created_at': row['created_at'],
                'updated_at': row.get('updated_at'),
                'product_name': product.get('name', 'Unknown Product') if product else 'Unknown Product',
                'product_id': product.get('id') if product else row['product_id']
            })
        return reviews

    def get_review_stats(self, product_id: str) -> Dict[str, Any]:
        """Get review statistics for a product (average rating, total count)."""
        # Get all reviews for this product
        result = self.supabase.table('reviews').select('rating').eq('product_id', product_id).execute()
        
        reviews = result.data or []
        total = len(reviews)
        
        if total == 0:
            return {
                'average_rating': 0,
                'total_reviews': 0,
                'rating_distribution': {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
            }
        
        # Calculate average
        total_rating = sum(r['rating'] for r in reviews)
        average = total_rating / total
        
        # Calculate distribution
        distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        for r in reviews:
            distribution[r['rating']] = distribution.get(r['rating'], 0) + 1
        
        return {
            'average_rating': round(average, 2),
            'total_reviews': total,
            'rating_distribution': distribution
        }

    def has_reviewed(self, user_id: str, product_id: str, order_id: str) -> bool:
        """Check if user has already reviewed this product for this order."""
        result = self.supabase.table('reviews').select('id').eq('user_id', user_id).eq('product_id', product_id).eq('order_id', order_id).limit(1).execute()
        return len(result.data or []) > 0

    def has_reviewed_product(self, user_id: str, product_id: str) -> bool:
        """Check if user has reviewed this product (any order)."""
        result = self.supabase.table('reviews').select('id').eq('user_id', user_id).eq('product_id', product_id).limit(1).execute()
        return len(result.data or []) > 0

    def get_review_by_id(self, review_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific review by ID."""
        result = self.supabase.table('reviews').select('*'
        ).eq('id', review_id).single().execute()
        review = result.data if result.data else None
        if review:
            # Fetch user and product data separately to avoid FK relationship issues
            if review.get('user_id'):
                user_result = self.supabase.table('users').select('id, first_name, last_name').eq('id', review['user_id']).single().execute()
                review['user'] = user_result.data if user_result.data else None
            if review.get('product_id'):
                product_result = self.supabase.table('products').select('id, name, seller_id').eq('id', review['product_id']).single().execute()
                review['product'] = product_result.data if product_result.data else None
        return review

    def update_review(self, review_id: str, user_id: str, rating: int = None, 
                      comment: str = None, image_url: str = None) -> bool:
        """Update a review (only if user owns it)."""
        data = {}
        if rating is not None:
            data['rating'] = rating
        if comment is not None:
            data['comment'] = comment
        if image_url is not None:
            data['image_url'] = image_url
        
        if not data:
            return False
        
        result = self.supabase.table('reviews').update(data).eq('id', review_id).eq('user_id', user_id).execute()
        return len(result.data or []) > 0

    def delete_review(self, review_id: str, user_id: str) -> bool:
        """Delete a review (only if user owns it)."""
        result = self.supabase.table('reviews').delete().eq('id', review_id).eq('user_id', user_id).execute()
        return len(result.data or []) > 0

    def can_review(self, user_id: str, product_id: str, order_id: str) -> Dict[str, Any]:
        """
        Check if a user can review a product from an order.
        Returns dict with 'can_review' boolean and 'reason' if not allowed.
        """
        # Check if order exists and belongs to user
        order_result = self.supabase.table('orders').select('id, buyer_id, status').eq('id', order_id).single().execute()
        
        if not order_result.data:
            return {'can_review': False, 'reason': 'Order not found'}
        
        order = order_result.data
        if order.get('buyer_id') != user_id:
            return {'can_review': False, 'reason': 'This order does not belong to you'}
        
        if order.get('status') != 'delivered':
            return {'can_review': False, 'reason': 'Reviews can only be submitted for delivered orders'}
        
        # Check if product is in this order
        item_result = self.supabase.table('order_items').select('id').eq('order_id', order_id).eq('product_id', product_id).limit(1).execute()
        
        if not item_result.data:
            return {'can_review': False, 'reason': 'This product was not in your order'}
        
        # Check if already reviewed
        if self.has_reviewed(user_id, product_id, order_id):
            return {'can_review': False, 'reason': 'You have already reviewed this product'}
        
        return {'can_review': True, 'reason': None}
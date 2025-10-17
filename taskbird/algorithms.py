# taskbird/algorithms.py
"""
Simple algorithms for Help Desk Ticket Management System
Implements: 1) Round-Robin Assignment, 2) Priority Scoring, 3) Response Time Prediction
"""

from django.contrib.auth import get_user_model
from django.db.models import Count, Q, Avg
from datetime import datetime, timedelta
import re

User = get_user_model()


# ============================================================================
# ALGORITHM 1: ROUND-ROBIN AUTO-ASSIGNMENT
# ============================================================================

class RoundRobinAssignment:
    """
    Assigns tickets to agents in a circular manner based on their current workload.
    Time Complexity: O(n) where n is the number of available agents
    """
    
    @staticmethod
    def get_available_agents(category=None):
        """Get all active agents, optionally filtered by category expertise"""
        # Assuming agents have is_staff=True or you have a custom role field
        agents = User.objects.filter(
            is_staff=True, 
            is_active=True
        )
        
        # You can extend this to filter by category if you add agent expertise
        return agents
    
    @staticmethod
    def assign_ticket(ticket):
        """
        Assign ticket to the agent with the least current workload
        Returns: Assigned agent or None
        """
        from .models import Ticket
        
        # Get available agents
        available_agents = RoundRobinAssignment.get_available_agents(ticket.category)
        
        if not available_agents.exists():
            return None
        
        # Count active tickets per agent (workload calculation)
        agents_with_workload = available_agents.annotate(
            active_ticket_count=Count(
                'assigned_tickets',
                filter=Q(
                    assigned_tickets__is_active=True,
                    assigned_tickets__status__name__in=['Open', 'In Progress', 'Pending']
                )
            )
        ).order_by('active_ticket_count', 'id')  # Sort by workload, then by ID for consistency
        
        # Assign to agent with minimum workload
        selected_agent = agents_with_workload.first()
        ticket.agent = selected_agent
        ticket.save()
        
        return selected_agent


# ============================================================================
# ALGORITHM 2: KEYWORD-BASED PRIORITY SCORING
# ============================================================================

class PriorityScoring:
    """
    Calculates priority score based on keywords in title and description.
    Score ranges: 0-100 (higher = more urgent)
    """
    
    # Define urgency keywords with weights
    URGENCY_KEYWORDS = {
        'critical': 30,
        'urgent': 25,
        'emergency': 30,
        'asap': 20,
        'immediately': 25,
        'down': 20,
        'not working': 15,
        'broken': 15,
        'crash': 20,
        'error': 10,
        'failed': 15,
        'unable': 10,
        'cannot': 10,
        'stuck': 12,
        'blocked': 15,
        'issue': 5,
        'problem': 5,
        'help': 3,
    }
    
    CUSTOMER_IMPACT_KEYWORDS = {
        'all users': 25,
        'multiple users': 20,
        'everyone': 20,
        'production': 25,
        'live': 20,
        'client': 15,
        'customer': 10,
    }
    
    @staticmethod
    def calculate_score(title, description):
        """
        Calculate priority score based on keyword analysis
        Returns: score (0-100)
        """
        text = f"{title} {description}".lower()
        score = 0
        
        # Check urgency keywords
        for keyword, weight in PriorityScoring.URGENCY_KEYWORDS.items():
            if keyword in text:
                score += weight
        
        # Check customer impact keywords
        for keyword, weight in PriorityScoring.CUSTOMER_IMPACT_KEYWORDS.items():
            if keyword in text:
                score += weight
        
        # Bonus: Check for multiple exclamation marks (indicates urgency)
        exclamation_count = text.count('!')
        score += min(exclamation_count * 5, 15)  # Max 15 points from exclamations
        
        # Normalize score to 0-100 range
        score = min(score, 100)
        
        return score
    
    @staticmethod
    def assign_priority(ticket):
        """
        Assign priority level based on calculated score
        Updates ticket priority field
        """
        from .models import Priority
        
        score = PriorityScoring.calculate_score(ticket.title, ticket.description)
        
        # Map score to priority levels
        # Assuming Priority levels: 1=Low, 2=Medium, 3=High, 4=Critical
        try:
            if score >= 60:
                priority = Priority.objects.get(level=4)  # Critical
            elif score >= 40:
                priority = Priority.objects.get(level=3)  # High
            elif score >= 20:
                priority = Priority.objects.get(level=2)  # Medium
            else:
                priority = Priority.objects.get(level=1)  # Low
            
            ticket.priority = priority
            ticket.save()
            
            return priority, score
        except Priority.DoesNotExist:
            return None, score


# ============================================================================
# ALGORITHM 3: RESPONSE TIME PREDICTION (Linear Regression Approach)
# ============================================================================

class ResponseTimePredictor:
    """
    Predicts estimated resolution time based on historical data.
    Uses simple averaging with category and priority factors.
    """
    
    @staticmethod
    def calculate_average_resolution_time(category=None, priority=None):
        """
        Calculate average resolution time based on historical tickets
        Returns: timedelta object or None
        """
        from .models import Ticket
        
        # Filter resolved tickets
        resolved_tickets = Ticket.objects.filter(
            resolved_at__isnull=False,
            created_at__isnull=False
        )
        
        # Apply filters if provided
        if category:
            resolved_tickets = resolved_tickets.filter(category=category)
        if priority:
            resolved_tickets = resolved_tickets.filter(priority=priority)
        
        if not resolved_tickets.exists():
            return None
        
        # Calculate resolution times
        total_time = timedelta()
        count = 0
        
        for ticket in resolved_tickets:
            resolution_time = ticket.resolved_at - ticket.created_at
            total_time += resolution_time
            count += 1
        
        # Return average
        if count > 0:
            avg_seconds = total_time.total_seconds() / count
            return timedelta(seconds=avg_seconds)
        
        return None
    
    @staticmethod
    def predict_resolution_time(ticket):
        """
        Predict resolution time for a ticket
        Returns: dict with prediction details
        """
        # Try to get category-priority specific average
        specific_avg = ResponseTimePredictor.calculate_average_resolution_time(
            category=ticket.category,
            priority=ticket.priority
        )
        
        # Fallback to category average
        if not specific_avg and ticket.category:
            specific_avg = ResponseTimePredictor.calculate_average_resolution_time(
                category=ticket.category
            )
        
        # Fallback to priority average
        if not specific_avg and ticket.priority:
            specific_avg = ResponseTimePredictor.calculate_average_resolution_time(
                priority=ticket.priority
            )
        
        # Final fallback to overall average
        if not specific_avg:
            specific_avg = ResponseTimePredictor.calculate_average_resolution_time()
        
        # Default to 24 hours if no historical data
        if not specific_avg:
            specific_avg = timedelta(hours=24)
        
        # Calculate estimated resolution datetime
        estimated_resolution = ticket.created_at + specific_avg
        
        return {
            'estimated_time': specific_avg,
            'estimated_resolution_date': estimated_resolution,
            'hours': specific_avg.total_seconds() / 3600,
            'formatted_time': ResponseTimePredictor._format_timedelta(specific_avg)
        }
    
    @staticmethod
    def _format_timedelta(td):
        """Format timedelta to human-readable string"""
        total_seconds = int(td.total_seconds())
        days = total_seconds // 86400
        hours = (total_seconds % 86400) // 3600
        minutes = (total_seconds % 3600) // 60
        
        parts = []
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")
        
        return " ".join(parts) if parts else "< 1m"


# ============================================================================
# UTILITY FUNCTION: PROCESS NEW TICKET
# ============================================================================

def process_new_ticket(ticket):
    """
    Apply all algorithms to a new ticket:
    1. Calculate and assign priority
    2. Auto-assign to agent
    3. Predict resolution time
    
    Returns: dict with processing results
    """
    results = {
        'ticket': ticket,
        'priority_assigned': False,
        'agent_assigned': False,
        'prediction': None
    }
    
    # 1. Priority Scoring
    priority, score = PriorityScoring.assign_priority(ticket)
    if priority:
        results['priority_assigned'] = True
        results['priority_score'] = score
        results['priority'] = priority
    
    # 2. Auto-assignment
    agent = RoundRobinAssignment.assign_ticket(ticket)
    if agent:
        results['agent_assigned'] = True
        results['assigned_agent'] = agent
    
    # 3. Time Prediction
    prediction = ResponseTimePredictor.predict_resolution_time(ticket)
    results['prediction'] = prediction
    
    return results
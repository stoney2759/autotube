"""
Workflow scheduler for YouTube Shorts Automation System.
Manages timing of content generation and workflow execution.
"""
import logging
import signal
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Callable, List, Union
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.job import Job
from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED, EVENT_JOB_MISSED
import threading

from utils.error_handling import WorkflowError, log_execution_time

logger = logging.getLogger(__name__)

class WorkflowScheduler:
    """
    Manages scheduling and execution of workflow jobs.
    """
    
    def __init__(self, max_concurrent_jobs: int = 1):
        """
        Initialize the workflow scheduler.
        
        Args:
            max_concurrent_jobs: Maximum number of concurrent jobs allowed
        """
        self.logger = logging.getLogger(__name__)
        self.scheduler = BackgroundScheduler()
        self.active_jobs = {}
        self.job_results = {}
        self.job_statuses = {}
        self.lock = threading.Lock()
        self.max_concurrent_jobs = max_concurrent_jobs
        self.running_jobs_count = 0
        
        # Register event listeners for job events
        self.scheduler.add_listener(self._job_executed_event, EVENT_JOB_EXECUTED)
        self.scheduler.add_listener(self._job_error_event, EVENT_JOB_ERROR)
        self.scheduler.add_listener(self._job_missed_event, EVENT_JOB_MISSED)
        
        # Start the scheduler
        self.scheduler.start()
        
        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._handle_shutdown_signal)
        signal.signal(signal.SIGTERM, self._handle_shutdown_signal)
        
        self.logger.info("Workflow scheduler initialized")
    
    def schedule_workflow(
        self, 
        workflow_id: str, 
        workflow_func: Callable, 
        interval_minutes: int = 60, 
        args: List = None, 
        kwargs: Dict[str, Any] = None, 
        start_now: bool = True,
        max_instances: int = 1,
        coalesce: bool = True
    ) -> Optional[Job]:
        """
        Schedule a workflow to run at specified intervals.
        
        Args:
            workflow_id: Unique identifier for the workflow
            workflow_func: Function to execute for the workflow
            interval_minutes: Minutes between workflow executions
            args: Positional arguments for the workflow function
            kwargs: Keyword arguments for the workflow function
            start_now: Whether to run the workflow immediately once
            max_instances: Maximum instances of this job that can run simultaneously
            coalesce: Whether to combine missed runs into a single run
            
        Returns:
            Scheduled job or None if scheduling failed
            
        Raises:
            WorkflowError: If the job cannot be scheduled
        """
        with self.lock:
            # Check if workflow already scheduled
            if workflow_id in self.active_jobs:
                self.logger.warning(f"Workflow {workflow_id} already scheduled. Removing old schedule.")
                self.remove_workflow(workflow_id)
            
            # Initialize arguments
            if args is None:
                args = []
            if kwargs is None:
                kwargs = {}
            
            try:
                # Add job to scheduler
                next_run_time = datetime.now() if start_now else None
                
                # Create wrapped function to track concurrent jobs
                wrapped_func = self._wrap_workflow_func(workflow_func, workflow_id)
                
                job = self.scheduler.add_job(
                    wrapped_func,
                    trigger=IntervalTrigger(minutes=interval_minutes),
                    id=workflow_id,
                    name=workflow_id,
                    args=args,
                    kwargs=kwargs,
                    next_run_time=next_run_time,
                    max_instances=max_instances,
                    coalesce=coalesce
                )
                
                # Record job in active jobs
                self.active_jobs[workflow_id] = job
                self.job_statuses[workflow_id] = "scheduled"
                
                self.logger.info(
                    f"Workflow {workflow_id} scheduled to run every {interval_minutes} minutes"
                    f"{' (starting now)' if start_now else ''}"
                )
                
                return job
            except Exception as e:
                self.logger.error(f"Error scheduling workflow {workflow_id}: {str(e)}")
                raise WorkflowError(f"Failed to schedule workflow: {str(e)}") from e
    
    def schedule_one_time_workflow(
        self, 
        workflow_id: str, 
        workflow_func: Callable, 
        run_date: Optional[datetime] = None,
        args: List = None, 
        kwargs: Dict[str, Any] = None
    ) -> Optional[Job]:
        """
        Schedule a workflow to run once at a specific time.
        
        Args:
            workflow_id: Unique identifier for the workflow
            workflow_func: Function to execute for the workflow
            run_date: When to run the workflow (None for immediate execution)
            args: Positional arguments for the workflow function
            kwargs: Keyword arguments for the workflow function
            
        Returns:
            Scheduled job or None if scheduling failed
        """
        with self.lock:
            # Check if workflow already scheduled
            if workflow_id in self.active_jobs:
                self.logger.warning(f"Workflow {workflow_id} already scheduled. Removing old schedule.")
                self.remove_workflow(workflow_id)
            
            # Initialize arguments
            if args is None:
                args = []
            if kwargs is None:
                kwargs = {}
            
            # Set default run date to now if not provided
            if run_date is None:
                run_date = datetime.now()
            
            try:
                # Create wrapped function to track concurrent jobs
                wrapped_func = self._wrap_workflow_func(workflow_func, workflow_id)
                
                job = self.scheduler.add_job(
                    wrapped_func,
                    trigger=DateTrigger(run_date=run_date),
                    id=workflow_id,
                    name=workflow_id,
                    args=args,
                    kwargs=kwargs
                )
                
                # Record job in active jobs
                self.active_jobs[workflow_id] = job
                self.job_statuses[workflow_id] = "scheduled"
                
                self.logger.info(f"One-time workflow {workflow_id} scheduled for {run_date}")
                
                return job
            except Exception as e:
                self.logger.error(f"Error scheduling one-time workflow {workflow_id}: {str(e)}")
                return None
    
    def remove_workflow(self, workflow_id: str) -> bool:
        """
        Remove a scheduled workflow.
        
        Args:
            workflow_id: ID of the workflow to remove
            
        Returns:
            True if the workflow was removed, False otherwise
        """
        with self.lock:
            if workflow_id in self.active_jobs:
                try:
                    self.scheduler.remove_job(workflow_id)
                except Exception as e:
                    self.logger.error(f"Error removing job {workflow_id} from scheduler: {str(e)}")
                
                # Clean up our tracking
                del self.active_jobs[workflow_id]
                self.job_statuses[workflow_id] = "removed"
                
                self.logger.info(f"Workflow {workflow_id} removed from schedule")
                return True
            else:
                self.logger.warning(f"Attempted to remove non-existent workflow: {workflow_id}")
                return False
    
    def pause_workflow(self, workflow_id: str) -> bool:
        """
        Pause a scheduled workflow.
        
        Args:
            workflow_id: ID of the workflow to pause
            
        Returns:
            True if the workflow was paused, False otherwise
        """
        with self.lock:
            if workflow_id in self.active_jobs:
                try:
                    self.scheduler.pause_job(workflow_id)
                    self.job_statuses[workflow_id] = "paused"
                    self.logger.info(f"Workflow {workflow_id} paused")
                    return True
                except Exception as e:
                    self.logger.error(f"Error pausing workflow {workflow_id}: {str(e)}")
                    return False
            else:
                self.logger.warning(f"Attempted to pause non-existent workflow: {workflow_id}")
                return False
    
    def resume_workflow(self, workflow_id: str) -> bool:
        """
        Resume a paused workflow.
        
        Args:
            workflow_id: ID of the workflow to resume
            
        Returns:
            True if the workflow was resumed, False otherwise
        """
        with self.lock:
            if workflow_id in self.active_jobs:
                try:
                    self.scheduler.resume_job(workflow_id)
                    self.job_statuses[workflow_id] = "running"
                    self.logger.info(f"Workflow {workflow_id} resumed")
                    return True
                except Exception as e:
                    self.logger.error(f"Error resuming workflow {workflow_id}: {str(e)}")
                    return False
            else:
                self.logger.warning(f"Attempted to resume non-existent workflow: {workflow_id}")
                return False
    
    def pause_all(self) -> None:
        """Pause all scheduled workflows."""
        with self.lock:
            self.scheduler.pause()
            for job_id in self.active_jobs:
                self.job_statuses[job_id] = "paused"
            self.logger.info("All workflows paused")
    
    def resume_all(self) -> None:
        """Resume all scheduled workflows."""
        with self.lock:
            self.scheduler.resume()
            for job_id in self.active_jobs:
                self.job_statuses[job_id] = "scheduled"
            self.logger.info("All workflows resumed")
    
    def get_job_status(self, workflow_id: str) -> Optional[str]:
        """
        Get the status of a workflow job.
        
        Args:
            workflow_id: ID of the workflow
            
        Returns:
            Status of the workflow or None if not found
        """
        with self.lock:
            return self.job_statuses.get(workflow_id)
    
    def get_all_jobs_status(self) -> Dict[str, Dict[str, Any]]:
        """
        Get status information for all jobs.
        
        Returns:
            Dictionary with job IDs as keys and status info as values
        """
        with self.lock:
            status_info = {}
            
            for job_id, job in self.active_jobs.items():
                next_run = job.next_run_time
                
                status_info[job_id] = {
                    "status": self.job_statuses.get(job_id, "unknown"),
                    "next_run": next_run.isoformat() if next_run else None,
                    "interval": str(job.trigger.interval) if hasattr(job.trigger, 'interval') else "one-time"
                }
            
            return status_info
    
    def get_job_result(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the latest result for a workflow job.
        
        Args:
            workflow_id: ID of the workflow
            
        Returns:
            Latest result or None if no results available
        """
        with self.lock:
            return self.job_results.get(workflow_id)
    
    def _wrap_workflow_func(self, func: Callable, workflow_id: str) -> Callable:
        """
        Wrap the workflow function to track execution and handle concurrency.
        
        Args:
            func: Original workflow function
            workflow_id: ID of the workflow
            
        Returns:
            Wrapped function
        """
        @log_execution_time(logger=self.logger)
        def wrapped_func(*args, **kwargs):
            # Update job status to running
            with self.lock:
                self.job_statuses[workflow_id] = "running"
                self.running_jobs_count += 1
                current_count = self.running_jobs_count
            
            self.logger.info(
                f"Starting workflow {workflow_id} (Running jobs: {current_count}/{self.max_concurrent_jobs})"
            )
            
            start_time = time.time()
            result = None
            success = False
            error_msg = None
            
            try:
                # Check if we're exceeding max concurrent jobs
                if current_count > self.max_concurrent_jobs:
                    self.logger.warning(
                        f"Max concurrent jobs ({self.max_concurrent_jobs}) exceeded. "
                        f"Workflow {workflow_id} will proceed anyway."
                    )
                
                # Execute the workflow function
                result = func(*args, **kwargs)
                success = True
                return result
            except Exception as e:
                error_msg = str(e)
                self.logger.error(f"Error in workflow {workflow_id}: {error_msg}")
                raise
            finally:
                # Update job status and store result
                end_time = time.time()
                duration = end_time - start_time
                
                with self.lock:
                    if success:
                        self.job_statuses[workflow_id] = "scheduled"  # Reset to scheduled for next run
                    else:
                        self.job_statuses[workflow_id] = "error"
                    
                    self.running_jobs_count -= 1
                    
                    # Store result info
                    self.job_results[workflow_id] = {
                        "timestamp": datetime.now().isoformat(),
                        "duration": duration,
                        "success": success,
                        "error": error_msg,
                        "result": result
                    }
                
                self.logger.info(
                    f"Completed workflow {workflow_id} in {duration:.2f}s "
                    f"(Running jobs: {self.running_jobs_count}/{self.max_concurrent_jobs})"
                )
        
        return wrapped_func
    
    def _job_executed_event(self, event):
        """Handle job executed event."""
        job_id = event.job_id
        with self.lock:
            if job_id in self.job_statuses and self.job_statuses[job_id] != "removed":
                self.job_statuses[job_id] = "scheduled"  # Reset to scheduled for next run
    
    def _job_error_event(self, event):
        """Handle job error event."""
        job_id = event.job_id
        with self.lock:
            if job_id in self.job_statuses:
                self.job_statuses[job_id] = "error"
                self.logger.error(f"Job {job_id} failed with exception: {event.exception}")
    
    def _job_missed_event(self, event):
        """Handle job missed event."""
        job_id = event.job_id
        scheduled_run_time = event.scheduled_run_time
        
        self.logger.warning(
            f"Job {job_id} missed scheduled run time at {scheduled_run_time}"
        )
    
    def _handle_shutdown_signal(self, signum, frame):
        """Handle shutdown signals (SIGINT, SIGTERM)."""
        self.logger.info(f"Received shutdown signal {signum}, shutting down scheduler")
        self.shutdown()
    
    def shutdown(self):
        """Shut down the scheduler."""
        self.logger.info("Shutting down scheduler")
        self.scheduler.shutdown()
        self.logger.info("Workflow scheduler shut down")
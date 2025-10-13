"""
Background job service for Climate TRACE data synchronization
"""
import os
import logging
import asyncio
from datetime import datetime, date, timedelta
from typing import Optional
from sqlalchemy.orm import Session

from ..db import get_db
from .climate_trace import climate_trace_service

logger = logging.getLogger(__name__)

# Feature flag
CT_ENABLED = os.getenv("COMPLIANCE_CT_ENABLED", "false").lower() == "true"

# Job configuration
CT_SYNC_INTERVAL_HOURS = int(os.getenv("CT_SYNC_INTERVAL_HOURS", "24"))  # Default 24 hours
CT_LOOKBACK_MONTHS = int(os.getenv("CT_LOOKBACK_MONTHS", "12"))  # Default 12 months


class ClimateTraceBackgroundJob:
    """Background job for Climate TRACE data synchronization and cross-checking"""
    
    def __init__(self):
        self.enabled = CT_ENABLED
        self.running = False
        self.last_run = None
        self.next_run = None
        
    async def start(self):
        """Start the background job"""
        if not self.enabled:
            logger.info("Climate TRACE background job disabled")
            return
        
        logger.info("Starting Climate TRACE background job")
        self.running = True
        
        while self.running:
            try:
                await self._run_sync_cycle()
                self.last_run = datetime.utcnow()
                self.next_run = self.last_run + timedelta(hours=CT_SYNC_INTERVAL_HOURS)
                
                # Wait for next cycle
                await asyncio.sleep(CT_SYNC_INTERVAL_HOURS * 3600)
                
            except Exception as e:
                logger.error(f"Error in Climate TRACE background job: {e}")
                # Wait 1 hour before retrying on error
                await asyncio.sleep(3600)
    
    def stop(self):
        """Stop the background job"""
        logger.info("Stopping Climate TRACE background job")
        self.running = False
    
    async def _run_sync_cycle(self):
        """Run a single sync cycle"""
        logger.info("Running Climate TRACE sync cycle")
        
        # Get database session
        db = next(get_db())
        
        try:
            # Sync recent months
            end_date = date.today()
            start_date = end_date - timedelta(days=CT_LOOKBACK_MONTHS * 30)
            
            current_date = start_date
            while current_date <= end_date:
                year = current_date.year
                month = current_date.month
                
                logger.info(f"Syncing Climate TRACE data for {year}-{month:02d}")
                
                # Run cross-check analysis
                crosschecks = climate_trace_service.run_crosscheck_analysis(
                    db, year, month
                )
                
                logger.info(f"Created {len(crosschecks)} cross-check records for {year}-{month:02d}")
                
                # Move to next month
                if current_date.month == 12:
                    current_date = current_date.replace(year=current_date.year + 1, month=1)
                else:
                    current_date = current_date.replace(month=current_date.month + 1)
            
            logger.info("Climate TRACE sync cycle completed successfully")
            
        except Exception as e:
            logger.error(f"Error in sync cycle: {e}")
            raise
        finally:
            db.close()
    
    async def run_manual_sync(self, year: int, month: int) -> bool:
        """Run manual sync for specific year/month"""
        if not self.enabled:
            logger.warning("Climate TRACE integration disabled")
            return False
        
        logger.info(f"Running manual Climate TRACE sync for {year}-{month:02d}")
        
        db = next(get_db())
        try:
            crosschecks = climate_trace_service.run_crosscheck_analysis(
                db, year, month
            )
            
            logger.info(f"Manual sync completed: {len(crosschecks)} cross-check records created")
            return True
            
        except Exception as e:
            logger.error(f"Error in manual sync: {e}")
            return False
        finally:
            db.close()
    
    def get_status(self) -> dict:
        """Get job status information"""
        return {
            "enabled": self.enabled,
            "running": self.running,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "next_run": self.next_run.isoformat() if self.next_run else None,
            "sync_interval_hours": CT_SYNC_INTERVAL_HOURS,
            "lookback_months": CT_LOOKBACK_MONTHS
        }


# Global job instance
ct_background_job = ClimateTraceBackgroundJob()


async def start_ct_background_job():
    """Start the Climate TRACE background job"""
    await ct_background_job.start()


def stop_ct_background_job():
    """Stop the Climate TRACE background job"""
    ct_background_job.stop()


async def run_manual_ct_sync(year: int, month: int) -> bool:
    """Run manual Climate TRACE sync"""
    return await ct_background_job.run_manual_sync(year, month)


def get_ct_job_status() -> dict:
    """Get Climate TRACE job status"""
    return ct_background_job.get_status()

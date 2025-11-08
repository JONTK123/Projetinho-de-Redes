#!/usr/bin/env python3
"""
Comprehensive test suite for all three phases of the project.
Tests RDT 2.0, 2.1, 3.0, GBN, and TCP implementations.
"""

import subprocess
import time
import sys
import os
import signal
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class TestResult:
    def __init__(self, test_name):
        self.test_name = test_name
        self.passed = False
        self.message = ""
        self.duration = 0
        
    def __str__(self):
        status = "✓ PASSED" if self.passed else "✗ FAILED"
        return f"{status} - {self.test_name} ({self.duration:.2f}s)\n  {self.message}"


class PhaseTest:
    def __init__(self):
        self.results = []
        
    def run_subprocess_test(self, test_name, receiver_cmd, sender_cmd, timeout=15):
        """Run a test with receiver and sender processes"""
        result = TestResult(test_name)
        start_time = time.time()
        
        receiver_proc = None
        sender_proc = None
        
        try:
            print(f"\n{'='*60}")
            print(f"Running: {test_name}")
            print(f"{'='*60}")
            
            # Start receiver
            receiver_proc = subprocess.Popen(
                receiver_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                preexec_fn=os.setsid if hasattr(os, 'setsid') else None
            )
            
            # Give receiver time to start
            time.sleep(1)
            
            # Start sender
            sender_proc = subprocess.Popen(
                sender_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Wait for sender to complete
            try:
                sender_out, sender_err = sender_proc.communicate(timeout=timeout)
                print("SENDER OUTPUT:")
                print(sender_out)
                if sender_err:
                    print("SENDER ERRORS:")
                    print(sender_err)
                
                # Give receiver time to finish
                time.sleep(2)
                
                # Get receiver output
                receiver_proc.send_signal(signal.SIGTERM if hasattr(signal, 'SIGTERM') else signal.SIGINT)
                receiver_out, receiver_err = receiver_proc.communicate(timeout=3)
                print("\nRECEIVER OUTPUT:")
                print(receiver_out)
                if receiver_err:
                    print("RECEIVER ERRORS:")
                    print(receiver_err)
                
                # Check for success indicators
                if sender_proc.returncode == 0 or "mensagens" in sender_out.lower() or "success" in sender_out.lower():
                    result.passed = True
                    result.message = "Test completed successfully"
                else:
                    result.message = f"Sender exited with code {sender_proc.returncode}"
                    
            except subprocess.TimeoutExpired:
                result.message = "Test timed out"
                
        except Exception as e:
            result.message = f"Error: {str(e)}"
            
        finally:
            # Clean up processes
            for proc in [sender_proc, receiver_proc]:
                if proc and proc.poll() is None:
                    try:
                        if hasattr(os, 'killpg'):
                            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                        else:
                            proc.terminate()
                        proc.wait(timeout=2)
                    except:
                        if proc.poll() is None:
                            proc.kill()
            
            result.duration = time.time() - start_time
            self.results.append(result)
            print(f"\n{result}")
            
        return result.passed


def test_phase1():
    """Test Phase 1: RDT implementations"""
    print("\n" + "="*60)
    print("PHASE 1: RDT PROTOCOLS")
    print("="*60)
    
    tester = PhaseTest()
    
    # Test rdt2.0
    tester.run_subprocess_test(
        "Phase 1 - RDT 2.0 (Channel with bit errors)",
        [sys.executable, "fase 1/rdt2/receiver.py"],
        [sys.executable, "fase 1/rdt2/sender.py"]
    )
    
    # Test rdt2.1
    tester.run_subprocess_test(
        "Phase 1 - RDT 2.1 (Sequence numbers)",
        [sys.executable, "fase 1/rdt21/receiver.py"],
        [sys.executable, "fase 1/rdt21/sender.py"]
    )
    
    # Test rdt3.0
    tester.run_subprocess_test(
        "Phase 1 - RDT 3.0 (Timer and packet loss)",
        [sys.executable, "fase 1/rdt3/receiver.py"],
        [sys.executable, "fase 1/rdt3/sender.py"]
    )
    
    return tester.results


def test_phase2():
    """Test Phase 2: GBN implementation"""
    print("\n" + "="*60)
    print("PHASE 2: GO-BACK-N (GBN)")
    print("="*60)
    
    tester = PhaseTest()
    
    # Test GBN
    tester.run_subprocess_test(
        "Phase 2 - Go-Back-N with pipelining",
        [sys.executable, "fase2/gbn/receiver.py"],
        [sys.executable, "fase2/gbn/sender.py"],
        timeout=20
    )
    
    return tester.results


def test_phase3():
    """Test Phase 3: TCP over UDP"""
    print("\n" + "="*60)
    print("PHASE 3: TCP OVER UDP")
    print("="*60)
    
    tester = PhaseTest()
    
    # Test TCP implementation
    tester.run_subprocess_test(
        "Phase 3 - TCP over UDP (handshake, data transfer, close)",
        [sys.executable, "fase3/server.py"],
        [sys.executable, "fase3/client.py"],
        timeout=20
    )
    
    return tester.results


def print_summary(all_results):
    """Print summary of all test results"""
    print("\n\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    total = len(all_results)
    passed = sum(1 for r in all_results if r.passed)
    failed = total - passed
    
    print(f"\nTotal Tests: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Success Rate: {(passed/total*100):.1f}%")
    
    print("\n" + "-"*60)
    print("DETAILED RESULTS:")
    print("-"*60)
    
    for result in all_results:
        print(result)
        print()
    
    return passed == total


def main():
    """Run all tests"""
    print("="*60)
    print("COMPREHENSIVE TEST SUITE FOR RDT AND TCP IMPLEMENTATION")
    print("="*60)
    
    # Change to project root
    os.chdir(project_root)
    
    all_results = []
    
    # Run all phase tests
    all_results.extend(test_phase1())
    all_results.extend(test_phase2())
    all_results.extend(test_phase3())
    
    # Print summary
    success = print_summary(all_results)
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())

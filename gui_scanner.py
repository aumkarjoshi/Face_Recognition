import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from PIL import Image, ImageTk
import cv2
import numpy as np
import torch
import threading
import os
import time
import subprocess
from pathlib import Path
from datetime import datetime
from collections import deque
import sys

from face_match import (
    compute_embeddings,
    load_reference_embedding,
    create_display_image,
    check_liveness,
    MTCNN,
    InceptionResnetV1
)


class IDScannerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Face Recognition System - ID Scanner Integration")
        self.root.geometry("1200x700")
        self.root.configure(bg="#f0f0f0")
        
        # Variables
        self.scanned_id_image = None
        self.scanned_id_path = None
        self.reference_encoding = None
        self.device = None
        self.mtcnn = None
        self.resnet = None
        self.camera_running = False
        self.verification_complete = False
        
        # Initialize models
        self.setup_models()
        
        # Create UI
        self.create_ui()
        
    def setup_models(self):
        """Initialize face recognition models"""
        try:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            self.mtcnn = MTCNN(keep_all=True, device=self.device)
            self.resnet = InceptionResnetV1(pretrained="vggface2").eval().to(self.device)
            status_msg = f"Models loaded (Device: {self.device})"
        except Exception as e:
            status_msg = f"Error loading models: {str(e)}"
            messagebox.showerror("Model Error", status_msg)
        
    def create_ui(self):
        """Create the main UI"""
        # Header
        header_frame = tk.Frame(self.root, bg="#2c3e50", height=60)
        header_frame.pack(fill=tk.X, padx=0, pady=0)
        
        title_label = tk.Label(
            header_frame,
            text="🔐 Face Recognition System - ID Scanner Integration",
            font=("Arial", 16, "bold"),
            bg="#2c3e50",
            fg="white"
        )
        title_label.pack(pady=15)
        
        # Main container
        main_container = tk.Frame(self.root, bg="#f0f0f0")
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Left panel - ID Scanner
        left_panel = tk.LabelFrame(
            main_container,
            text="Step 1: Scan ID Document",
            font=("Arial", 12, "bold"),
            bg="white",
            padx=15,
            pady=15
        )
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Scanner buttons
        button_frame = tk.Frame(left_panel, bg="white")
        button_frame.pack(pady=10)
        
        self.scan_btn = tk.Button(
            button_frame,
            text="📱 Scan ID Document",
            command=self.scan_id,
            font=("Arial", 11, "bold"),
            bg="#3498db",
            fg="white",
            padx=20,
            pady=12,
            cursor="hand2",
            relief=tk.RAISED,
            bd=2
        )
        self.scan_btn.pack(pady=5)
        
        self.manual_btn = tk.Button(
            button_frame,
            text="📂 Select Image Manually",
            command=self.select_image_manually,
            font=("Arial", 10),
            bg="#95a5a6",
            fg="white",
            padx=20,
            pady=10,
            cursor="hand2"
        )
        self.manual_btn.pack(pady=5)
        
        # ID Preview
        preview_label = tk.Label(left_panel, text="ID Preview:", font=("Arial", 10, "bold"), bg="white")
        preview_label.pack(anchor=tk.W, pady=(10, 5))
        
        self.id_preview_frame = tk.Frame(left_panel, bg="lightgray", height=250)
        self.id_preview_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.id_preview_label = tk.Label(
            self.id_preview_frame,
            text="[ID Image Preview]",
            font=("Arial", 12),
            bg="lightgray",
            fg="gray"
        )
        self.id_preview_label.pack(expand=True)
        
        # ID Info
        info_frame = tk.Frame(left_panel, bg="white")
        info_frame.pack(fill=tk.X, pady=10)
        
        self.id_status_label = tk.Label(
            info_frame,
            text="Status: No ID scanned",
            font=("Arial", 10),
            bg="white",
            fg="#e74c3c"
        )
        self.id_status_label.pack(anchor=tk.W)
        
        # Right panel - Face Recognition
        right_panel = tk.LabelFrame(
            main_container,
            text="Step 2: Face Recognition Verification",
            font=("Arial", 12, "bold"),
            bg="white",
            padx=15,
            pady=15
        )
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Start verification button
        self.verify_btn = tk.Button(
            right_panel,
            text="▶ Start Face Verification",
            command=self.start_verification,
            font=("Arial", 11, "bold"),
            bg="#27ae60",
            fg="white",
            padx=20,
            pady=12,
            cursor="hand2",
            relief=tk.RAISED,
            bd=2,
            state=tk.DISABLED
        )
        self.verify_btn.pack(pady=10)
        
        # Camera feed
        camera_label = tk.Label(right_panel, text="Camera Feed:", font=("Arial", 10, "bold"), bg="white")
        camera_label.pack(anchor=tk.W, pady=(10, 5))
        
        self.camera_frame = tk.Frame(right_panel, bg="black", height=300)
        self.camera_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.camera_label = tk.Label(
            self.camera_frame,
            text="[Camera Feed - Click 'Start Face Verification']",
            font=("Arial", 12),
            bg="black",
            fg="gray"
        )
        self.camera_label.pack(expand=True)
        
        # Status
        status_label = tk.Label(right_panel, text="Verification Status:", font=("Arial", 10, "bold"), bg="white")
        status_label.pack(anchor=tk.W, pady=(10, 5))
        
        self.verify_status_label = tk.Label(
            right_panel,
            text="Ready to verify",
            font=("Arial", 10),
            bg="white",
            fg="#3498db"
        )
        self.verify_status_label.pack(anchor=tk.W)
        
        # Footer
        footer_frame = tk.Frame(self.root, bg="#34495e", height=40)
        footer_frame.pack(fill=tk.X, padx=0, pady=0, side=tk.BOTTOM)
        
        footer_label = tk.Label(
            footer_frame,
            text="🔒 Strict Liveness Detection Enabled | Spoof-Proof Technology",
            font=("Arial", 9),
            bg="#34495e",
            fg="white"
        )
        footer_label.pack(pady=8)
    
    def scan_id(self):
        """Launch Assure ID scanner"""
        try:
            self.scan_btn.config(state=tk.DISABLED, text="⏳ Scanning...")
            self.root.update()
            
            # Try to find and launch Assure ID
            assure_id_paths = [
                r"C:\Program Files\IDEMIA\AssureID Professional\AssureID.exe",
                r"C:\Program Files (x86)\IDEMIA\AssureID Professional\AssureID.exe",
                r"C:\Program Files\TTM SYSTEMS\AssureID\AssureID.exe",
                r"C:\Program Files (x86)\TTM SYSTEMS\AssureID\AssureID.exe",
            ]
            
            assure_id_found = False
            for path in assure_id_paths:
                if os.path.exists(path):
                    assure_id_found = True
                    messagebox.showinfo(
                        "ID Scanner",
                        "Assure ID will open shortly.\n\n"
                        "Instructions:\n"
                        "1. Place your ID on the scanner\n"
                        "2. Wait for the scan to complete\n"
                        "3. Click 'Save' or 'Complete' in Assure ID\n"
                        "4. Then select the scanned image from the dialog"
                    )
                    subprocess.Popen(path)
                    break
            
            if not assure_id_found:
                messagebox.showwarning(
                    "Scanner Not Found",
                    "Assure ID not found in default locations.\n\n"
                    "Please select the scanned image manually or:\n"
                    "1. Open Assure ID manually\n"
                    "2. Scan your ID\n"
                    "3. Save the image\n"
                    "4. Click 'Select Image Manually' button"
                )
                self.select_image_manually()
                return
            
            # Wait for user to complete scan
            time.sleep(2)
            
            # Try to find recently saved image from Assure ID default location
            self.root.after(5000, self.find_scanned_image)
            
        except Exception as e:
            messagebox.showerror("Scanner Error", f"Error launching scanner:\n{str(e)}")
            self.scan_btn.config(state=tk.NORMAL, text="📱 Scan ID Document")
    
    def find_scanned_image(self):
        """Find and load the recently scanned image"""
        common_paths = [
            os.path.expanduser("~\\Documents\\AssureID"),
            os.path.expanduser("~\\AppData\\Local\\IDEMIA\\AssureID"),
            os.path.expanduser("~\\Pictures"),
            r"C:\Users\Public\Pictures",
        ]
        
        found = False
        for search_path in common_paths:
            if os.path.exists(search_path):
                try:
                    files = list(Path(search_path).glob("*.jpg")) + list(Path(search_path).glob("*.png"))
                    if files:
                        # Get most recent file
                        latest_file = max(files, key=os.path.getctime)
                        if time.time() - os.path.getctime(latest_file) < 120:  # File less than 2 minutes old
                            self.load_scanned_image(str(latest_file))
                            found = True
                            break
                except:
                    continue
        
        if not found:
            messagebox.showinfo(
                "Select Image",
                "Please navigate to your scanned image and select it."
            )
            self.select_image_manually()
        
        self.scan_btn.config(state=tk.NORMAL, text="📱 Scan ID Document")
    
    def select_image_manually(self):
        """Let user select ID image manually"""
        file_path = filedialog.askopenfilename(
            title="Select Scanned ID Image",
            filetypes=[
                ("Image files", "*.jpg *.jpeg *.png *.bmp"),
                ("JPEG", "*.jpg *.jpeg"),
                ("PNG", "*.png"),
                ("All files", "*.*")
            ]
        )
        
        if file_path:
            self.load_scanned_image(file_path)
    
    def load_scanned_image(self, image_path):
        """Load and process the scanned ID image"""
        try:
            # Read the image
            image = cv2.imread(image_path)
            if image is None:
                messagebox.showerror("Error", "Could not read the image file")
                return
            
            # Store the image
            self.scanned_id_image = image
            self.scanned_id_path = image_path
            
            # Extract embeddings
            try:
                self.reference_encoding = load_reference_embedding(image_path, self.mtcnn, self.resnet)
            except Exception as e:
                messagebox.showerror("Face Detection Error", f"No face detected in ID image:\n{str(e)}")
                self.scanned_id_image = None
                self.scanned_id_path = None
                self.scan_btn.config(state=tk.NORMAL)
                return
            
            # Display preview
            self.display_id_preview(image)
            
            # Update status
            self.id_status_label.config(
                text=f"✓ ID Scanned: {os.path.basename(image_path)}",
                fg="#27ae60"
            )
            
            # Enable verification button
            self.verify_btn.config(state=tk.NORMAL)
            
            messagebox.showinfo("Success", "ID image loaded successfully!\n\nNow click 'Start Face Verification'")
            
        except Exception as e:
            messagebox.showerror("Error", f"Error loading image:\n{str(e)}")
            self.scan_btn.config(state=tk.NORMAL)
    
    def display_id_preview(self, image):
        """Display ID image preview in the preview frame"""
        try:
            # Resize for preview
            display_image = create_display_image(image, width=250)
            
            # Convert to RGB for PIL
            image_rgb = cv2.cvtColor(display_image, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(image_rgb)
            
            # Convert to PhotoImage
            photo = ImageTk.PhotoImage(pil_image)
            
            # Update label
            self.id_preview_label.config(image=photo, text="")
            self.id_preview_label.image = photo
            
        except Exception as e:
            print(f"Error displaying preview: {e}")
    
    def start_verification(self):
        """Start the face verification process"""
        if self.scanned_id_image is None:
            messagebox.showwarning("No ID", "Please scan an ID first")
            return
        
        self.verify_btn.config(state=tk.DISABLED)
        self.camera_running = True
        self.verification_complete = False
        
        # Run verification in a separate thread
        verification_thread = threading.Thread(target=self.run_face_verification, daemon=True)
        verification_thread.start()
    
    def run_face_verification(self):
        """Run the actual face verification with camera"""
        try:
            capture = cv2.VideoCapture(0)
            if not capture.isOpened():
                messagebox.showerror("Camera Error", "Unable to open camera")
                self.verify_btn.config(state=tk.NORMAL)
                self.camera_running = False
                return
            
            print("Starting face verification...")
            start_time = time.time()
            time_limit = 15
            matched = False
            live_verified = False
            frame_buffer = deque(maxlen=2)
            blink_history = deque(maxlen=10)
            
            while self.camera_running and time.time() - start_time < time_limit:
                ret, frame = capture.read()
                if not ret:
                    break
                
                frame_buffer.append(frame.copy())
                face_embeddings, boxes = compute_embeddings(frame, self.mtcnn, self.resnet)
                
                status_text = "No face detected"
                status_color = (0, 255, 255)
                liveness_text = ""
                liveness_color = (0, 0, 255)
                
                if face_embeddings.shape[0] > 0 and boxes.shape[0] > 0:
                    status_text = "Face detected"
                    distances = np.linalg.norm(face_embeddings - self.reference_encoding, axis=1)
                    
                    for box, distance in zip(boxes, distances):
                        is_live, liveness_score, liveness_reason = check_liveness(frame, box, frame_buffer, blink_history)
                        
                        face_matched = distance <= 0.8
                        
                        if face_matched and is_live:
                            matched = True
                            live_verified = True
                            color = (0, 255, 0)
                            label = f"MATCH {distance:.2f} (Live)"
                            status_text = "ID Match confirmed + Live face verified"
                            status_color = (0, 255, 0)
                            liveness_text = "LIVENESS: PASSED"
                            liveness_color = (0, 255, 0)
                        else:
                            color = (0, 0, 255)
                            if face_matched and not is_live:
                                label = f"SPOOF DETECTED!"
                                status_text = "Face matches but SPOOF DETECTED"
                                status_color = (0, 0, 255)
                                liveness_text = f"LIVENESS: FAILED"
                                liveness_color = (0, 0, 255)
                            else:
                                label = f"No match {distance:.2f}"
                                status_text = "Face does not match ID"
                                status_color = (0, 0, 255)
                                liveness_text = "LIVENESS: FAILED"
                                liveness_color = (0, 0, 255)
                        
                        left, top, right, bottom = [int(v) for v in box]
                        cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
                        cv2.rectangle(frame, (left, bottom - 26), (right, bottom), color, cv2.FILLED)
                        cv2.putText(frame, label, (left + 4, bottom - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                        
                        score_text = f"Liveness: {liveness_score:.2f}"
                        cv2.putText(frame, score_text, (left, top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, liveness_color, 1)
                
                elapsed = time.time() - start_time
                timer_text = f"Time: {elapsed:.1f}/{time_limit}s"
                cv2.putText(frame, timer_text, (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                cv2.putText(frame, status_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.9, status_color, 2)
                
                if liveness_text:
                    cv2.putText(frame, liveness_text, (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, liveness_color, 2)
                
                # Display frame
                self.display_camera_frame(frame)
                
                # Check for key press
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    break
                
                if matched and live_verified:
                    break
            
            capture.release()
            
            # Show result
            self.camera_running = False
            if matched and live_verified:
                self.show_verification_result(True, "ID ACCEPTED + LIVE PERSON VERIFIED")
            elif matched and not live_verified:
                self.show_verification_result(False, "SPOOF/PHOTO ATTACK DETECTED")
            else:
                self.show_verification_result(False, "FACE DOES NOT MATCH ID")
            
        except Exception as e:
            print(f"Error during verification: {e}")
            messagebox.showerror("Verification Error", f"Error during verification:\n{str(e)}")
        finally:
            self.camera_running = False
            self.verify_btn.config(state=tk.NORMAL)
    
    def display_camera_frame(self, frame):
        """Display camera frame in GUI"""
        try:
            # Resize for display
            display_frame = cv2.resize(frame, (640, 480))
            
            # Convert to RGB for PIL
            frame_rgb = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
            pil_frame = Image.fromarray(frame_rgb)
            
            # Convert to PhotoImage
            photo = ImageTk.PhotoImage(pil_frame)
            
            # Update label
            self.camera_label.config(image=photo, text="")
            self.camera_label.image = photo
            self.root.update()
            
        except Exception as e:
            print(f"Error displaying frame: {e}")
    
    def show_verification_result(self, success, message):
        """Show verification result"""
        self.camera_running = False
        
        if success:
            self.verify_status_label.config(text=f"✓ {message}", fg="#27ae60")
            messagebox.showinfo("Verification Successful", message)
        else:
            self.verify_status_label.config(text=f"✗ {message}", fg="#e74c3c")
            messagebox.showerror("Verification Failed", message)
        
        self.verify_btn.config(state=tk.NORMAL)


def main():
    root = tk.Tk()
    app = IDScannerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()

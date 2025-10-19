import socket
import threading
from customtkinter import *

class ChatClient:
    def __init__(self):
        self.sock = None
        self.nickname = None
        self.host = None
        self.port = None
        self.running = False
        self.buffer = ""

        self.win = CTk()
        self.win.geometry("400x300")
        self.win.title("Chat")

        CTkLabel(self.win, text="Nickname:").pack(pady=5)
        self.nickname_entry = CTkEntry(self.win)
        self.nickname_entry.pack(pady=5)

        CTkLabel(self.win, text="Host:").pack(pady=5)
        self.host_entry = CTkEntry(self.win)
        self.host_entry.pack(pady=5)

        CTkLabel(self.win, text="Port:").pack(pady=5)
        self.port_entry = CTkEntry(self.win)
        self.port_entry.pack(pady=5)

        CTkButton(self.win, text="Login", command=self.connect_server).pack(pady=20)
        self.win.protocol("WM_DELETE_WINDOW", self.close_client)
        self.win.mainloop()

    def connect_server(self):
        self.host = self.host_entry.get().strip() or "127.0.0.1"
        self.nickname = self.nickname_entry.get().strip() or "Anon"
        try:
            self.port = int(self.port_entry.get().strip() or 8081)
        except ValueError:
            return

        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.host, self.port))
            self.sock.send(self.nickname.encode('utf-8'))
        except:
            return

        self.running = True
        self.open_chat_window()
        threading.Thread(target=self.receive_messages, daemon=True).start()

    def open_chat_window(self):
        self.chat_root = self.win
        self.chat_root.title(f"Чат ({self.nickname})")
        self.chat_root.geometry("700x500")

        for w in self.chat_root.winfo_children():
            w.destroy()

        main_frame = CTkFrame(self.chat_root)
        main_frame.pack(side="left", fill="both", expand=True, padx=10, pady=10)

        self.text_area = CTkTextbox(main_frame, wrap="word", state="disabled")
        self.text_area.pack(fill="both", expand=True, pady=5)

        entry_frame = CTkFrame(main_frame)
        entry_frame.pack(fill="x")

        self.entry = CTkEntry(entry_frame)
        self.entry.pack(side="left", fill="x", expand=True, padx=5, pady=5)
        self.entry.bind("<Return>", lambda e: self.send_message())

        CTkButton(entry_frame, text="Send", width=50, command=self.send_message).pack(side="right", padx=5)

        side_frame = CTkFrame(self.chat_root, width=150)
        side_frame.pack(side="right", fill="y", padx=10, pady=10)

        CTkLabel(side_frame, text="Користувачі").pack(pady=10)
        self.user_list = CTkTextbox(side_frame, state="disabled", width=120)
        self.user_list.pack(fill="both", expand=True, padx=5, pady=5)

        self.chat_root.protocol("WM_DELETE_WINDOW", self.close_client)

    def receive_messages(self):
        while self.running:
            try:
                data = self.sock.recv(4096)
                if not data:
                    break
                self.buffer += data.decode('utf-8')

                while "\n" in self.buffer:
                    line, self.buffer = self.buffer.split("\n", 1)
                    if line.startswith("MSG:"):
                        self.chat_root.after_idle(self.add_message, line[4:])
                    elif line.startswith("USERS:"):
                        users = [u.strip() for u in line[6:].split(",") if u.strip()]
                        self.chat_root.after_idle(self.update_user_list, users)

            except:
                break

        self.running = False
        self.chat_root.after_idle(self.add_message, "З'єднання втрачено.")

    def add_message(self, text):
        self.text_area.configure(state="normal")
        self.text_area.insert("end", text + "\n")
        self.text_area.see("end")
        self.text_area.configure(state="disabled")

    def update_user_list(self, users):
        self.user_list.configure(state="normal")
        self.user_list.delete("1.0", "end")
        for u in users:
            if "(" in u and ")" in u:
                name, count = u.split("(")
                count = count.replace(")", "").strip()
                self.user_list.insert("end", f"{name.strip()}: {count}\n")
        self.user_list.configure(state="disabled")

    def send_message(self):
        msg = self.entry.get().strip()
        if not msg:
            return
        try:
            self.sock.send(msg.encode('utf-8'))
        except:
            self.add_message("Помилка відправлення.")
        self.entry.delete(0, "end")

    def close_client(self):
        self.running = False
        try:
            if self.sock:
                self.sock.close()
        except:
            pass
        self.win.destroy()


if __name__ == "__main__":
    ChatClient()

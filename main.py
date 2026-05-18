import psycopg2
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, font
from datetime import date, timedelta
import datetime
import bcrypt
from PIL import Image, ImageTk
import os
import logging
import shutil
import json
from config import get_connection

SESSION_FILE = "session.json"

def save_session(user_id):
    with open(SESSION_FILE, "w", encoding="utf-8") as f:
        json.dump({"user_id": user_id}, f, ensure_ascii=False)

def load_session():
    if os.path.exists(SESSION_FILE):
        try:
            with open(SESSION_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("user_id")
        except Exception:
            pass
    return None

def clear_session():

    if os.path.exists(SESSION_FILE):
        os.remove(SESSION_FILE)

os.makedirs("logs", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(filename)s:%(lineno)d | %(message)s',
    handlers=[
        logging.StreamHandler(),  # Вывод в консоль
        logging.FileHandler('logs/app.log', encoding='utf-8', mode='a')  # В файл
    ]
)

class NutritionApp:
    def __init__(self, root):
        self.bg_color = "#fefffc"

        self.root = root
        self.root.title("Трекер питания")
        self.root.geometry("700x500")
        
        self.main_frame = tk.Frame(root, bg=self.bg_color)      
        
        # Инициализация хранилищ
        self.meal_imgs = {}
        self.meal_tables = {}
        self.meal_buttons = {}
        
        self.add_frame = tk.Frame(root, bg=self.bg_color)       # Экран добавления продукта
        self.product_frame = tk.Frame(root, bg=self.bg_color)
        self.auth_frame = tk.Frame(root, bg=self.bg_color)

        self.avatar_path = "img/userIcon/avatar.png"
        img = Image.open(self.avatar_path).resize((50, 50), Image.Resampling.LANCZOS)
        self.avatar_img = ImageTk.PhotoImage(img)

        self.app_icon = self.load_resized_avatar("img/appIcon/apple.png", (200, 200))
        self.back_img = self.load_resized_avatar("img/systemIcon/back.png", (50, 50))

        self.fonts = ["Segoe UI", "Arial"]

        if not hasattr(self, 'meal_imgs'): self.meal_imgs = {}

        self.selected_products = []
        self.current_user_id = None
        self.current_log_id = None 

        self.current_day = datetime.date.today()
        
        
        self.current_meal_type_id = 1 
        self.meal_tables = {}    

        self.total_calories = 0 
        self.total_proteins = 0 
        self.total_fats = 0 
        self.total_carbs = 0 

                # Флаги режима работы product_frame
        self.app_mode = "add"       # "add" или "edit"
        self.edit_item_id = None    
        
        # Контекстное меню (правая кнопка мыши)
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="Изменить вес", command=self.edit_from_context)
        self.context_menu.add_command(label="Удалить", command=self.delete_from_context)

        
        self.setup_auth_screen()
        
        auto_id = load_session()
        if auto_id:
            self.current_user_id = auto_id
            self.init_daily_log(self.current_day)
            
            # Загружаем аватарку из БД
            try:
                conn = get_connection()
                cur = conn.cursor()
                cur.execute("SELECT avatar_path FROM Users WHERE user_id = %s", (self.current_user_id,))
                row = cur.fetchone()
                self.avatar_path = row[0] if row and row[0] else "img/userIcon/avatar.png"
                if not os.path.exists(self.avatar_path): self.avatar_path = "img/userIcon/avatar.png"
                self.avatar_img = self.load_resized_avatar(self.avatar_path)
                cur.close()
                conn.close()
            except: pass

            self.setup_main_screen()
            self.show_frame(self.main_frame)
        else:
            self.show_frame(self.auth_frame)



    def load_resized_avatar(self, path, max_size=(60, 60)):
        try:
            img = Image.open(path)
            # thumbnail изменяет изображение "на месте", подгоняя под max_size без искажений
            img.thumbnail(max_size, Image.Resampling.LANCZOS) 
            return ImageTk.PhotoImage(img)
        except Exception:
            # Если файл битый или не найден → подгружаем дефолтный
            default = "img/userIcon/avatar.png"
            img = Image.open(default)
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            return ImageTk.PhotoImage(img)
        

    def get_safe_font(self, font_names, size=10, weight="normal"):

        available = font.families()
        
        for name in font_names:
            if any(name.lower() == f.lower() for f in available):
                return (name, size, weight)

        logging.warning(f"Ни один шрифт из {font_names} не найден. Использую TkDefaultFont")
        return ("TkDefaultFont", size, weight)


    def init_daily_log(self, day):
        """Находит или создаёт запись в daily_logs на текущую дату"""
        
        try:
                conn = get_connection()
                cur = conn.cursor()
                
                # есть ли уже запись на сегодня
                cur.execute("""
                    SELECT log_id, total_calories, total_proteins, total_fats, total_carbs  
                    FROM daily_logs 
                    WHERE user_id = %s AND log_date = %s
                """, (self.current_user_id, day))
                
                result = cur.fetchall()
                
                if result:
                    self.current_log_id = result[0][0]
                    print(f"Найден дневник на {self.current_day} (ID: {self.current_log_id})")
                    self.total_calories, self.total_proteins, self.total_fats, self.total_carbs = float(result[0][1]), float(result[0][2]), float(result[0][3]), float(result[0][4])
                    
                else:
                    # cоздаём новую запись с нулевыми показателями
                    cur.execute("""
                        INSERT INTO daily_logs (user_id, log_date, total_calories, total_proteins, total_fats, total_carbs)
                        VALUES (%s, %s, 0, 0, 0, 0)
                        RETURNING log_id
                    """, (self.current_user_id, day))
                    
                    self.current_log_id = cur.fetchone()[0]
                    self.total_calories, self.total_proteins, self.total_fats, self.total_carbs = 0,0,0,0
                    conn.commit()
                    print(f" Создан новый дневник на {self.current_day} (ID: {self.current_log_id})")
                    
                cur.close()
                conn.close()
        except Exception as e:
                messagebox.showerror("Ошибка БД", f"Не удалось инициализировать дневник:\n{e}")
                self.current_log_id = None  
    
    def show_frame(self, frame):
        """Скрываем всё, показываем нужный фрейм"""
        self.main_frame.pack_forget()
        self.add_frame.pack_forget()
        self.product_frame.pack_forget()
        self.auth_frame.pack_forget()
        frame.pack(fill="both", expand=True)



    def setup_auth_screen(self):
        for widget in self.auth_frame.winfo_children():
            widget.destroy()

        tk.Label(self.auth_frame, image=self.app_icon, bg=self.bg_color).pack()

        tk.Label(self.auth_frame, text = "Дневник питания", font=self.get_safe_font(self.fonts, size=20, weight="bold"), 
                 bg=self.bg_color).pack(pady=20)
        tk.Label(self.auth_frame, text = "Войдите или создайте аккаунт", font=self.get_safe_font(self.fonts, size=14),
                 bg=self.bg_color).pack(pady=20)

        btn_frame = tk.Frame(self.auth_frame, bg=self.bg_color)
        btn_frame.pack(pady=10)

        tk.Button(btn_frame, text="Я новый пользователь", font=self.get_safe_font(self.fonts, size=14), width=30, 
                  height=1, bg="#9ee70c", command=self.show_registration_form).pack(pady=10)
        tk.Button(btn_frame, text="У меня уже есть аккаунт", command=self.show_login_form, width=30, height=1,
                  font=self.get_safe_font(self.fonts, size=14), bg=self.bg_color, fg="#669704").pack(pady=10)
        

#ВХОД
    def show_login_form(self):
        for widget in self.auth_frame.winfo_children():
            widget.destroy()

        tk.Button(self.auth_frame, image=self.back_img, command=self.setup_auth_screen, bg=self.bg_color,
                  relief="flat", bd=0).pack(anchor="nw")
        
        tk.Label(self.auth_frame, text="Войти", font=self.get_safe_font(self.fonts, size=16, weight="bold"),
                 bg=self.bg_color).pack(pady=30)

        tk.Label(self.auth_frame, text="Логин:", font=self.get_safe_font(self.fonts, size=14), bg=self.bg_color).pack()
        self.entry_login = tk.Entry(self.auth_frame, width=30, relief="groove", bd=4, 
                                    font=self.get_safe_font(self.fonts, size=14))
        self.entry_login.pack(pady=10)

        tk.Label(self.auth_frame, text="Пароль:", font=self.get_safe_font(self.fonts, size=14), bg=self.bg_color).pack()
        self.entry_pass = tk.Entry(self.auth_frame, width=30, relief="groove", bd=4, show="*", 
                                   font=self.get_safe_font(self.fonts, size=14))
        self.entry_pass.pack(pady=10)

        self.remember_var = tk.BooleanVar(value=False)
        tk.Checkbutton(self.auth_frame, text="Запомнить меня", font=self.get_safe_font(self.fonts, size=14),
                       bg=self.bg_color, variable=self.remember_var).pack(pady=5)

        tk.Button(self.auth_frame, text="Войти", font=self.get_safe_font(self.fonts, size=14), bg="#9ee70c",
                 command=self.process_login, width=30, height=1).pack(pady=20)
        


    def process_login(self):
        login = self.entry_login.get()
        password = self.entry_pass.get()

        if not login or not password:
            messagebox.showwarning("Внимание", "Заполните все поля!")
            return
        
        try:
            conn = get_connection()
            cur = conn.cursor()

            cur.execute("SELECT user_id, password_hash FROM users WHERE login = %s", (login,))
            row = cur.fetchone()
            

            if row is None: 
                messagebox.showerror("Ошибка", "Пользователь не найден")
                return
            
            user_id, stored_hash = row

            hash_bytes = stored_hash if isinstance(stored_hash, bytes) else stored_hash.encode('utf-8')
            
            if bcrypt.checkpw(password.encode('utf-8'), hash_bytes):
                self.current_user_id = user_id

                if self.remember_var.get():
                    save_session(user_id)

                self.init_daily_log(self.current_day)

                cur.execute("SELECT avatar_path FROM Users WHERE user_id = %s", (self.current_user_id,))
                self.avatar_path = cur.fetchone()[0] or "img/userIcon/avatar.png"

                # Проверка на случай если файл удалён
                if not os.path.exists(self.avatar_path):
                    self.avatar_path = "img/userIcon/avatar.png"

                self.avatar_img = self.load_resized_avatar(self.avatar_path)

                #self.avatar_img = tk.PhotoImage(file=avatar_path)
                print(self.avatar_path)
                self.setup_main_screen()  
                self.show_frame(self.main_frame)
                #messagebox.showinfo("Успех", f"Добро пожаловать, {login}!")
            else:
                messagebox.showerror("Ошибка", "Неверный пароль")

            

        
        except Exception as e:
            messagebox.showerror("Ошибка БД", str(e))

        finally:
            cur.close()
            conn.close()
            
#РЕГИСТРАЦИЯ 
    def show_registration_form(self):
        for widget in self.auth_frame.winfo_children():
            widget.destroy()

        tk.Button(self.auth_frame, image=self.back_img, command=self.setup_auth_screen, bg=self.bg_color,
                  relief="flat", bd=0).pack(anchor="nw")
        
        tk.Label(self.auth_frame, text="Создание аккаунта", font=self.get_safe_font(self.fonts, size=16, weight="bold"),
                 bg=self.bg_color).pack(pady=30)

        tk.Label(self.auth_frame, text="Логин:", font=self.get_safe_font(self.fonts, size=14), bg=self.bg_color).pack()
        self.reg_login = tk.Entry(self.auth_frame, width=30, relief="groove", bd=4, 
                                    font=self.get_safe_font(self.fonts, size=14))
        self.reg_login.pack(pady=10)

        tk.Label(self.auth_frame, text="Пароль:", font=self.get_safe_font(self.fonts, size=14), bg=self.bg_color).pack()
        self.reg_pass = tk.Entry(self.auth_frame, width=30, relief="groove", bd=4, 
                                    font=self.get_safe_font(self.fonts, size=14))
        self.reg_pass.pack(pady=10)

        tk.Label(self.auth_frame, text="Повторите пароль:", font=self.get_safe_font(self.fonts, size=14), bg=self.bg_color).pack()
        self.reg_pass_replay = tk.Entry(self.auth_frame, width=30, relief="groove", bd=4, 
                                    font=self.get_safe_font(self.fonts, size=14))
        self.reg_pass_replay.pack(pady=10)

        tk.Button(self.auth_frame, text="Зарегистрироваться", font=self.get_safe_font(self.fonts, size=14), width=30, 
                  command=self.process_registor, bg="#9ee70c", height=1).pack(pady=20)
        


    def process_registor(self):
        login = self.reg_login.get().strip()
        password = self.reg_pass.get()
        password_replay = self.reg_pass_replay.get()

        if not login or not password or not password_replay:
            messagebox.showwarning("Внимание", "Заполните все поля!")
            return
        
        if len(login) < 3 or len(login) > 255:
            messagebox.showwarning("Внимание", "Логин должен быть от 3 до 255 символов")
            return

        if password != password_replay:
            messagebox.showerror("Ошибка", "Пароли не совпадают")
            return
        
        try:
            conn = get_connection()
            cur = conn.cursor()

            cur.execute("SELECT user_id FROM users WHERE login = %s", (login,))
            if cur.fetchone():
                messagebox.showwarning("Внимание", "Логин уже существует")
                conn.close()
                cur.close()
                return
            

            hashed_bytes = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            hashed_str = hashed_bytes.decode('utf-8')

            cur.execute("INSERT INTO users(login, password_hash) VALUES (%s, %s) RETURNING user_id", (login, hashed_str))
            user_id = cur.fetchone()[0]
            self.current_user_id = user_id

            conn.commit()
            conn.close()
            cur.close()
            

            messagebox.showinfo("Успех", f"Добро пожаловать, {login}!")
            self.init_daily_log(self.current_day)
            self.setup_main_screen()
            self.show_frame(self.main_frame)
            

        except Exception as e:
            messagebox.showerror("Ошибка БД", str(e))
        


    def frame_for_meal(self, meal_type_id):
        meal_frame = tk.Frame(self.main_frame, bg=self.bg_color)
        meal_frame.pack(padx=5, pady=2)

        header_frame = tk.Frame(meal_frame, bg=self.bg_color)
        header_frame.pack()

        meal_config = {
        1: ("Завтрак", "img/systemIcon/breakfast.png"),
        2: ("Обед",    "img/systemIcon/lunch.png"),
        3: ("Ужин",    "img/systemIcon/dinner.png"),
        4: ("Перекус", "img/systemIcon/cheatmeal.png")
        }

        text, img_path = meal_config.get(meal_type_id, ("Приём пищи", "img/systemIcon/cheatmeal.png"))

        self.meal_imgs[meal_type_id] = self.load_resized_avatar(img_path, (40, 40))

        tk.Label(header_frame, image=self.meal_imgs[meal_type_id], text=text, compound="left", anchor="w", width=120, bg=self.bg_color,
                font=self.get_safe_font(self.fonts, size=12, weight="bold"), padx=10).pack(side="left")
        
        tk.Button(header_frame, text="Добавить продукт +", font=self.get_safe_font(self.fonts, size=10), bg="#9ee70c",
                 command=lambda: self.open_add_product_frame(meal_type_id),
                 width=20).pack(side="left", padx=5)
        
        if self.is_following_plan:
            tk.Button(header_frame, text="Применить план", font=self.get_safe_font(self.fonts, size=10),
                     command=lambda mid=meal_type_id: self.apply_plan_to_meal(mid), 
                     bg=self.bg_color, bd=2, relief="groove", width=14).pack(side="left", padx=3)
        
        btn_show = tk.Button(header_frame, text="⭣", font=self.get_safe_font(self.fonts, size=15, weight="bold"), 
                 command=lambda: self.toggle_meal_table(meal_type_id), relief="flat", fg="#669704", bg=self.bg_color)
        btn_show.pack(side="left", padx=5)
        self.meal_buttons[meal_type_id] = btn_show
        
        style = ttk.Style()
        style.configure("Treeview.Heading", font=self.get_safe_font(self.fonts, size=10))
        style.configure("mystyle.Treeview", font=self.get_safe_font(self.fonts, size=10))  # Шрифт для тела Treeview
        
        tree = ttk.Treeview(meal_frame, columns=("item_id", "product_id", "name", "weight", "cal", "prot", "fat", "carb"), show="headings", height=4)
        
        # Настраиваем видимые и скрытые колонки
        tree.column("item_id", width=0, stretch=False)
        tree.column("product_id", width=0, stretch=False)
        tree.heading("prot", text="Белки")
        tree.column("prot", width=10)
        tree.heading("fat", text="Жиры")
        tree.column("fat", width=10)
        tree.heading("carb", text="Углеводы")
        tree.column("carb", width=10)
        
        tree.heading("name", text="Продукт")
        tree.column("name", width=50)
        
        tree.heading("weight", text="Вес (г)")
        tree.column("weight", width=10)
        
        tree.heading("cal", text="Ккал")
        tree.column("cal", width=10)
        
        tree.pack(fill="x", pady=2)
        tree.pack_forget()
        self.meal_tables[meal_type_id] = tree

        #  Привязки событий
        tree.bind("<ButtonRelease-1>", lambda e, mid=meal_type_id: self.on_meal_click(e, mid))
        tree.bind("<Button-3>", self.on_right_click)

    def on_meal_click(self, event, meal_type_id):
        item = self.meal_tables[meal_type_id].selection()
        if not item: return
        
        values = self.meal_tables[meal_type_id].item(item[0])["values"]
        if not values: return  
        
        self.current_editing_meal_type = meal_type_id
        values = self.meal_tables[meal_type_id].item(item[0])["values"]
        
        # Сохраняем данные для редактирования
        self.edit_item_id = int(values[0])
        self.edit_product_id = int(values[1])
        self.edit_product_name = values[2]
        self.edit_weight = float(values[3])
        self.edit_nut = {
            'cal': float(values[4]), 'prot': float(values[5]),
            'fat': float(values[6]), 'carb': float(values[7])
        }
        
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""SELECT c.name FROM product_categories pc
                       JOIN category c ON pc.category_id = c.category_id
                       WHERE pc.product_id = %s LIMIT 1""", (self.edit_product_id,))
        cat_row = cur.fetchone()
        cur.close(); conn.close()
        self.current_category_str = cat_row[0] if cat_row else "Без категории"

        self.app_mode = "edit"
        self.setup_product_frame(mode="edit")
        self.show_frame(self.product_frame)

    def on_right_click(self, event):
        for tree in self.meal_tables.values():
            if tree.winfo_ismapped():
                item = tree.identify_row(event.y)
                if item:
                    tree.selection_set(item)
                    self.context_menu.tk_popup(event.x_root, event.y_root)
                break

    def edit_from_context(self):
        for mid, tree in self.meal_tables.items():
            if tree.winfo_ismapped() and tree.selection():
                self.on_meal_click(None, mid)
                break

    def delete_from_context(self):
        for mid, tree in self.meal_tables.items():
            if tree.winfo_ismapped() and tree.selection():
                self.delete_selected_item(mid)
                break
        

    def prev_day(self):
            self.current_day -= timedelta(days=1)
            self.on_date_change()

    def next_day(self):
            self.current_day += timedelta(days=1)
            self.on_date_change()

    def on_date_change(self):
        if self.current_day == datetime.date.today():
            date_text = "Сегодня"
        elif self.current_day == datetime.date.today() - datetime.timedelta(days=1):
            date_text = "Вчера"
        elif self.current_day == datetime.date.today() + datetime.timedelta(days=1):
            date_text = "Завтра"
        else:
            date_text = self.current_day.strftime("%d %B %Y")
            
        if hasattr(self, 'date_label'):
            self.date_label.config(text=date_text)

        self.init_daily_log(self.current_day)

        self.refresh_all_meals()

        if hasattr(self, 'cal_total'):
            self.cal_total.config(text=f"{self.total_calories:.0f} ккал")
            self.prot_total.config(text=f"Белки\n{self.total_proteins:.1f} г")
            self.fats_total.config(text=f"Жиры\n{self.total_fats:.1f} г")
            self.carbs_total.config(text=f"Углеводы\n{self.total_carbs:.1f} г")

        self.sync_plan_day_with_date()
    
    # ========== ГЛАВНЫЙ ЭКРАН ==========
    def setup_main_screen(self):
        for widget in self.main_frame.winfo_children():
            widget.destroy()

        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("SELECT 1 FROM User_Plans WHERE user_id = %s", (self.current_user_id,))
            self.is_following_plan = cur.fetchone() is not None
            cur.close()
            conn.close()
        except:
            self.is_following_plan = False


        up_frame = tk.Frame(self.main_frame, bg=self.bg_color)
        up_frame.pack(side="top", fill=tk.X)

        self.main_avatar_img = self.load_resized_avatar(self.avatar_path, (60, 60))

        self.main_avatar_btn = tk.Button(up_frame, image=self.main_avatar_img, command=self.setup_user_frame, bg=self.bg_color,
                                         bd=0, relief="flat", padx=0, pady=0, width=0, height=0)
        self.main_avatar_btn.image = self.avatar_img  
        self.main_avatar_btn.pack(side="left")

        tk.Button(up_frame, text="Узнать больше о планах питания ⭢", font=self.get_safe_font(self.fonts, size=10), bg=self.bg_color,
                  bd=3, padx=5, relief="groove", command=self.setup_plan_frame).pack(anchor="ne")
        # Заголовок
        if self.current_day == datetime.date.today(): text = "Сегодня"
        elif self.current_day == (datetime.date.today() + timedelta(days=1)): text = "Завтра"
        elif self.current_day == (datetime.date.today() - timedelta(days=1)): text = "Вчера"
        else: text = self.current_day

        calendar_frame = tk.Frame(self.main_frame, bg=self.bg_color)
        calendar_frame.pack()

        tk.Button(calendar_frame, text="<", font=self.get_safe_font(self.fonts, size=14), bd=3, relief="flat",
                  bg=self.bg_color, command=self.prev_day).pack(padx=10, side="left")
        self.date_label = tk.Label(calendar_frame, text=text, font=self.get_safe_font(self.fonts, size=14, weight="bold"),
                                   bg=self.bg_color)
        self.date_label.pack(padx=10, side="left")
        tk.Button(calendar_frame, text=">", font=self.get_safe_font(self.fonts, size=14), bd=3, relief="flat",
                  bg=self.bg_color, command=self.next_day).pack(padx=10, side="left")
        
        
        # Статистика
        total_frame = tk.Frame(self.main_frame, bg=self.bg_color)
        total_frame.pack(pady=10)

        self.cal_total = tk.Label(total_frame, text=f"{self.total_calories:.0f} ккал", bg=self.bg_color,
                                  font=self.get_safe_font(self.fonts, size=14, weight="bold"))
        self.cal_total.pack(padx=10, side="left")
        self.prot_total = tk.Label(total_frame, text=f"Белки \n{self.total_proteins:.1f}", bg=self.bg_color,
                                  font=self.get_safe_font(self.fonts, size=14))
        self.prot_total.pack(padx=10, side="left")
        self.fats_total = tk.Label(total_frame, text=f"Жиры \n{self.total_fats:.1f}", bg=self.bg_color,
                                  font=self.get_safe_font(self.fonts, size=14))
        self.fats_total.pack(padx=10, side="left")
        self.carbs_total = tk.Label(total_frame, text=f"Углеводы \n{self.total_carbs:.1f}", bg=self.bg_color,
                                  font=self.get_safe_font(self.fonts, size=14))
        self.carbs_total.pack(padx=10, side="left")
        
        self.frame_for_meal(1)
        self.frame_for_meal(2)
        self.frame_for_meal(3)
        self.frame_for_meal(4)



    def setup_user_frame(self):
        for w in self.add_frame.winfo_children(): w.destroy()

        tk.Button(self.add_frame, image=self.back_img, command=lambda: self.show_frame(self.main_frame), bg=self.bg_color,
                  relief="flat", bd=0).pack(anchor="nw")

        frame_user = tk.Frame(self.add_frame, bg=self.bg_color)
        frame_user.pack()

        self.user_avatar_img = self.load_resized_avatar(self.avatar_path, (150,150))

        self.user_avatar_btn = tk.Button(frame_user, image=self.user_avatar_img, command=self.change_icon, bd=0, 
                                         relief="flat", bg=self.bg_color)
        self.user_avatar_btn.pack(side="left",padx=20)

        personal_info_frame = tk.Frame(self.add_frame, bg=self.bg_color)
        personal_info_frame.pack()


        try:
            conn = get_connection()
            cur = conn.cursor()

            cur.execute("SELECT login, gender, weight, height, age, goal_type, target_weight, " \
                        " target_calories, is_folowing_plan " \
                        " FROM users " \
                        " WHERE user_id=%s", (self.current_user_id,))
            
            rows = cur.fetchall()
            self.user_login = rows[0][0]
            
            tk.Label(frame_user, text=f"Логин: {self.user_login}", bg=self.bg_color,
                     font=self.get_safe_font(self.fonts, size=14)).pack(pady=20, padx=20)
            tk.Button(frame_user, text="🖊 Изменить информацию", font=self.get_safe_font(self.fonts, size=10), bg="#9ee70c",
                      command=self.change_user_info, relief="groove", bd=1, width=40).pack()
            
            is_connected, plan_name = self.get_plan_status()

            if is_connected:
                # План подключён → кнопка "Отключить"
                btn_plan = tk.Button(frame_user, text=f"Отключить план «{plan_name}»", 
                                     font=self.get_safe_font(self.fonts, size=10), width=40,
                                     bg="#ffcccc", relief="groove", bd=1,
                                     command=self.toggle_plan_connection)
            else:
                # План не подключён → кнопка "Подключить"
                btn_plan = tk.Button(frame_user, text="Подключить план питания", 
                                     font=self.get_safe_font(self.fonts, size=10), width=30,
                                     bg="#ccffcc", fg="#006600", relief="groove", bd=1,
                                     command=self.toggle_plan_connection)
            btn_plan.pack(pady=5)

            self.setup_progress_widget(self.add_frame)

            tk.Button(self.add_frame, text="Выйти из аккаунта", command=self.logout, 
                  bg="#ea1515", fg="#ffffff", font=self.get_safe_font(self.fonts, size=14)).pack(pady=10)


            tk.Label(personal_info_frame, text=f"Пол: {("не указано" if not rows[0][1] else rows[0][1])} \n"\
                     f"Вес: {("не указано" if not rows[0][2] else rows[0][2])} \nРост: "\
                     f"{("не указано" if not rows[0][3] else rows[0][3])} \nВозраст: "\
                    f"{("не указано" if not rows[0][4] else rows[0][4])} \nЦель: "\
                    f"{("не указано" if not rows[0][5] else rows[0][5])} \nЦелевой вес: "\
                    f"{("не указано" if not rows[0][6] else rows[0][6])}", 
                    font=self.get_safe_font(self.fonts, size=14), bg=self.bg_color).pack(pady=20, side="left")

        except Exception as e:
            messagebox("Error", "ошибка бд")

        finally:
            cur.close()
            conn.close()

        
        self.show_frame(self.add_frame)

    def logout(self):
        """Полный выход: очистка сессии, сброс переменных, возврат на экран входа"""
        clear_session()
        self.current_user_id = None
        self.current_log_id = None
        self.selected_products.clear()
        
        # Сброс даты на сегодня
        self.current_day = datetime.date.today()
        
        messagebox.showinfo("Выход", "Вы вышли из аккаунта")
        self.show_frame(self.auth_frame)
        self.setup_auth_screen()


    def change_icon(self):
        filepath = filedialog.askopenfilename(
            title="Выберите аватар",
            filetypes=[("Изображения", "*.png *.jpg *.jpeg")]
        )
        if not filepath: return

        # Сохраняем под уникальным именем
        ext = os.path.splitext(filepath)[1]
        new_filename = f"avatar_{self.current_user_id}{ext}"
        save_path = os.path.join("img", "userIcon", new_filename)
        
        os.makedirs("img/userIcon", exist_ok=True)
        shutil.copy2(filepath, save_path)  # Копируем файл в проект

        # Обновляем путь в БД
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("UPDATE Users SET avatar_path = %s WHERE user_id = %s", 
                        (save_path, self.current_user_id))
            conn.commit()
            cur.close()
            conn.close()

            self.avatar_path = save_path

            if hasattr(self, 'main_avatar_btn'):
                self.main_avatar_img = self.load_resized_avatar(self.avatar_path, (60, 60))
                self.main_avatar_btn.config(image=self.main_avatar_img)

            if hasattr(self, 'user_avatar_btn'):
                self.user_avatar_img = self.load_resized_avatar(self.avatar_path, (150, 150))
                self.user_avatar_btn.config(image=self.user_avatar_img)

            messagebox.showinfo("Успех", "Аватар обновлён!")
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))
    

    def change_user_info(self):
        for w in self.add_frame.winfo_children(): w.destroy()

        tk.Button(self.add_frame, image=self.back_img, command=self.setup_user_frame, bg=self.bg_color,
                  relief="flat", bd=0).pack(anchor="nw")

        tk.Label(self.add_frame, text="Пол", font=self.get_safe_font(self.fonts, size=14), bg=self.bg_color).pack()
        self.gender_combobox = ttk.Combobox(self.add_frame, font=self.get_safe_font(self.fonts, size=14), 
                                            values=["мужской", "женский"], state="readonly")
        self.gender_combobox.pack()

        tk.Label(self.add_frame, text="Рост", font=self.get_safe_font(self.fonts, size=14), bg=self.bg_color).pack()
        self.height_spinbox = ttk.Spinbox(self.add_frame, from_=50, to=250, font=self.get_safe_font(self.fonts, size=14))
        self.height_spinbox.pack()

        tk.Label(self.add_frame, text="Вес", font=self.get_safe_font(self.fonts, size=14), bg=self.bg_color).pack()
        self.weight_spinbox = ttk.Spinbox(self.add_frame, from_=10.0, to=1000.0, 
                                          font=self.get_safe_font(self.fonts, size=14))
        self.weight_spinbox.pack()

        tk.Label(self.add_frame, text="Возраст", font=self.get_safe_font(self.fonts, size=14), bg=self.bg_color).pack()
        self.age_spinbox = ttk.Spinbox(self.add_frame, from_=0.0, to=150.0, 
                                       font=self.get_safe_font(self.fonts, size=14))
        self.age_spinbox.pack()

        tk.Label(self.add_frame, text="Цель", font=self.get_safe_font(self.fonts, size=14), bg=self.bg_color).pack()
        self.goal_combobox = ttk.Combobox(self.add_frame, values=["поддержание", "похудение", "набор"], state="readonly",
                                          font=self.get_safe_font(self.fonts, size=14))
        self.goal_combobox.pack()

        tk.Label(self.add_frame, text="Целевой вес", font=self.get_safe_font(self.fonts, size=14), bg=self.bg_color).pack()
        self.targer_weight_spinbox = ttk.Spinbox(self.add_frame, from_=10.0, to=1000.0, 
                                       font=self.get_safe_font(self.fonts, size=14))
        self.targer_weight_spinbox.pack()

        tk.Button(self.add_frame, text="Сохранить", command=self.save_info, width=30, 
                  font=self.get_safe_font(self.fonts, size=14), bg="#9ee70c").pack(pady=30)

        self.show_frame(self.add_frame)

    def toggle_plan_connection(self):
        """Переключает статус подключения плана: подключает или отключает"""
        try:
            conn = get_connection()
            cur = conn.cursor()
            
            # Проверяем, подключён ли план сейчас
            cur.execute("SELECT plan_id FROM User_Plans WHERE user_id = %s", (self.current_user_id,))
            current_plan = cur.fetchone()
            
            if current_plan:
                # 🔴 Отключаем план
                cur.execute("DELETE FROM User_Plans WHERE user_id = %s", (self.current_user_id,))
                cur.execute("UPDATE Users SET is_folowing_plan = FALSE WHERE user_id = %s", (self.current_user_id,))
                conn.commit()
                messagebox.showinfo("План отключён", "Вы больше не следуете плану питания.")
            else:
                # 🟢 Открываем выбор плана (если ещё не подключен)
                conn.commit()
                cur.close()
                conn.close()
                self.setup_plan_frame()  # Переход на экран выбора планов
                return  # Выходим, не закрывая соединение
            
            cur.close()
            conn.close()
            
            # Обновляем профиль, чтобы кнопка поменяла текст
            self.setup_user_frame()
            self.setup_main_screen()
            
        except Exception as e:
            messagebox.showerror("Ошибка БД", str(e))

    def get_plan_status(self):
        """Возвращает (is_connected, plan_name)"""
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("""
                SELECT mp.name 
                FROM User_Plans up
                JOIN Meal_Plans mp ON up.plan_id = mp.plan_id
                WHERE up.user_id = %s
            """, (self.current_user_id,))
            row = cur.fetchone()
            cur.close()
            conn.close()
            
            if row:
                return True, row[0]  # План подключён, возвращаем название
            return False, None
        except:
            return False, None

    def save_info(self):
        updates = {}
        if self.gender_combobox.current()!=-1: updates['gender'] = self.gender_combobox.get()

        h = self.height_spinbox.get().strip()
        if h:
            try:
                val = int(h)
                if 50 < val < 250: updates['height'] = val
            except ValueError: pass

        w = self.weight_spinbox.get().strip()
        new_weight = None
        if w:
            try:
                val = float(w)
                if val > 0: 
                    updates['weight'] = val
                    new_weight = val
            except ValueError: pass

        a = self.age_spinbox.get().strip()
        if a:
            try:
                val = int(a)
                if 10 < val < 120: updates['age'] = val
            except ValueError: pass
        if self.goal_combobox.current()!=-1: updates['goal_type'] = self.goal_combobox.get()

        tg = self.targer_weight_spinbox.get().strip()
        if tg:
            try:
                val = int(tg)
                if 10 < val < 1000: updates['target_weight'] = val
            except ValueError: pass

        if not updates:
            messagebox.showinfo("Инфо", "Заполните хотя бы одно поле для обновления")
            return

        set_clause = ", ".join(f"{col} = %s" for col in updates.keys())
        query = f"UPDATE users SET {set_clause} WHERE user_id = %s"
        values = list(updates.values()) + [self.current_user_id]

        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute(query, values)
            
            # 🔑 Если вес изменился → логируем в историю
            if new_weight:
                cur.execute("INSERT INTO User_Weight_Log (user_id, weight_kg) VALUES (%s, %s)", 
                            (self.current_user_id, new_weight))
            
            conn.commit()
            messagebox.showinfo("Успех", "Данные обновлены")
        except Exception as e:
            messagebox.showerror("Ошибка БД", str(e))
        finally:
            cur.close()
            conn.close()
            self.setup_user_frame()  # Обновит профиль и прогресс

    def save_weight_log(self, weight_kg):
        """Сохраняет взвешивание в историю"""
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("INSERT INTO User_Weight_Log (user_id, weight_kg) VALUES (%s, %s)",
                        (self.current_user_id, weight_kg))
            conn.commit()
            cur.close(); conn.close()
            return True
        except Exception as e:
            messagebox.showerror("Ошибка БД", str(e))
            return False

    def get_weight_progress(self):
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT weight, target_weight FROM Users WHERE user_id = %s", (self.current_user_id,))
        row = cur.fetchone()
        if not row or not row[1]:
            cur.close(); conn.close()
            return None
            
        db_weight, target = float(row[0]), float(row[1])
        
        # Берём первый и последний вес из лога. Если лога нет → берём текущий из Users
        cur.execute("SELECT weight_kg FROM User_Weight_Log WHERE user_id = %s ORDER BY log_id ASC LIMIT 1", (self.current_user_id,))
        init_row = cur.fetchone()
        initial = float(init_row[0]) if init_row else db_weight
        
        cur.execute("SELECT weight_kg FROM User_Weight_Log WHERE user_id = %s ORDER BY log_id DESC LIMIT 1", (self.current_user_id,))
        cur_row = cur.fetchone()
        current = float(cur_row[0]) if cur_row else db_weight
        
        cur.close(); conn.close()
        
        total_diff = abs(initial - target)
        if total_diff == 0: return {"status": "met", "current": current, "target": target}
        
        progress = min(100.0, max(0.0, (abs(initial - current) / total_diff) * 100))
        return {"initial": round(initial, 1), "current": round(current, 1), "target": target, "progress": round(progress, 1)}
    
    def setup_progress_widget(self, parent_frame):
        prog_frame = tk.Frame(parent_frame, bg=self.bg_color, relief="groove", bd=1)
        prog_frame.pack(fill="x", pady=10, padx=20)

        data = self.get_weight_progress()
        if not data:
            tk.Label(prog_frame, text="Укажите целевой вес в 'Изменить информацию'", 
                     font=self.get_safe_font(self.fonts, size=11), bg=self.bg_color, fg="#888").pack(pady=10)
            return

        tk.Label(prog_frame, text=f"🎯 Прогресс к цели: {data['progress']}%", 
                 font=self.get_safe_font(self.fonts, size=12, weight="bold"), bg=self.bg_color).pack(pady=(5,2))
        
        bar = ttk.Progressbar(prog_frame, orient="horizontal", length=350, mode="determinate")
        bar.pack(pady=2)
        bar["value"] = data["progress"]
        
        # Цвет бара в зависимости от прогресса
        if data["progress"] >= 75: bar.configure(style="Green.Horizontal.TProgressbar")
        elif data["progress"] >= 40: bar.configure(style="Yellow.Horizontal.TProgressbar")
        
        tk.Label(prog_frame, text=f"Старт: {data['initial']} кг  →  Сейчас: {data['current']} кг  →  Цель: {data['target']} кг",
                 font=self.get_safe_font(self.fonts, size=10), bg=self.bg_color, fg="#666").pack(pady=(2,5))

    def prompt_weight_entry(self):
        """Модальное окно для ввода веса"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Взвешивание")
        dialog.geometry("250x120")
        dialog.configure(bg=self.bg_color)
        dialog.transient(self.root)
        dialog.grab_set()

        tk.Label(dialog, text="Ваш текущий вес (кг):", bg=self.bg_color).pack(pady=10)
        w_var = tk.StringVar()
        tk.Entry(dialog, textvariable=w_var, font=("Arial", 12), justify="center").pack(fill="x", padx=20)

        def save():
            try:
                val = float(w_var.get())
                if val <= 0 or val > 300: raise ValueError
                if self.save_weight_log(val):
                    dialog.destroy()
                    # Обновляем виджет прогресса на главном экране
                    if hasattr(self, 'main_frame'):
                        self.setup_main_screen() 
            except ValueError:
                messagebox.showwarning("Ошибка", "Введите корректный вес!")

        tk.Button(dialog, text="Сохранить", command=save, bg="#9ee70c").pack(pady=5)


    def setup_plan_frame(self):
        for w in self.add_frame.winfo_children(): w.destroy()

        tk.Button(self.add_frame, image=self.back_img, command=lambda: self.show_frame(self.main_frame), bg=self.bg_color,
                  relief="flat", bd=0).pack(anchor="nw")

        tk.Label(self.add_frame, text="Доступные планы питания", font=self.get_safe_font(self.fonts, size=14, weight="bold"),
                 bg=self.bg_color).pack(pady=10)

        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("SELECT plan_id, name, description, target_calories FROM Meal_Plans WHERE is_active = TRUE ORDER BY target_calories")
            plans = cur.fetchall()
            cur.close()
            conn.close()

            if not plans:
                tk.Label(self.add_frame, text="Нет активных планов.").pack(pady=20)

            else:
                for p_id, name, desc, kcal in plans:
                    p_frame = tk.Frame(self.add_frame, bd=1, relief="groove", bg=self.bg_color)
                    p_frame.pack(fill="x", padx=20, pady=5)

                    tk.Label(p_frame, text=f"{name}", font=self.get_safe_font(self.fonts, size=14, weight="bold"),
                             bg=self.bg_color).pack(side="left", padx=10, pady=5)
                    tk.Label(p_frame, text=f"~{kcal} ккал/день", fg="green", font=self.get_safe_font(self.fonts, size=14),
                             bg=self.bg_color).pack(side="left", padx=10)
                    tk.Label(p_frame, text=desc, wraplength=250, font=self.get_safe_font(self.fonts, size=9),
                             bg=self.bg_color).pack(side="left", padx=10, fill="x", expand=True)

                    # При нажатии передаём plan_id в функцию деталей
                    tk.Button(p_frame, text="Подробнее", command=lambda pid=p_id: self.show_plan_details(pid), bd=0, relief="flat",
                              bg="#84C5FB", width=12, font=self.get_safe_font(self.fonts, size=14)).pack(side="right", padx=10, pady=5)
        except Exception as e:
            messagebox.showerror("Ошибка БД", str(e))

        self.show_frame(self.add_frame)


    def show_plan_details(self, plan_id):
        """Экран с подробным меню выбранного плана"""
        for w in self.add_frame.winfo_children(): w.destroy()
        tk.Button(self.add_frame, image=self.back_img, command=self.setup_plan_frame, bg=self.bg_color,
                  relief="flat", bd=0).pack(anchor="nw")

        try:
            conn = get_connection()
            cur = conn.cursor()

            tk.Label(self.add_frame, text="Пример первого дня", font=self.get_safe_font(self.fonts, size=14, weight="bold"),
                     bg=self.bg_color).pack()
            
            # Инфо о плане
            cur.execute("SELECT current_day_index FROM User_Plans WHERE user_id = %s", (self.current_user_id,))
            day_row = cur.fetchone()
            day_index = day_row[0] if day_row else 1

            cur.execute("""
                SELECT mt.meal_type_id, mt.name, p.name, ps.recommended_weight_g
                FROM Plan_Schedule ps
                JOIN Meal_Types mt ON ps.meal_type_id = mt.meal_type_id
                JOIN Products p ON ps.product_id = p.product_id
                WHERE ps.plan_id = %s AND ps.day_index = %s
                ORDER BY mt.meal_type_id
            """, (plan_id, day_index))
            rows = cur.fetchall()
            cur.close()
            conn.close()

            meal_config = {
                1: ("Завтрак", "img/systemIcon/breakfast.png"),
                2: ("Обед",    "img/systemIcon/lunch.png"),
                3: ("Ужин",    "img/systemIcon/dinner.png"),
                4: ("Перекус", "img/systemIcon/cheatmeal.png")
            }

            current_meal_id = None
            for meal_type_id, m_name, prod, w in rows:
                if meal_type_id != current_meal_id:
                    meal_header = tk.Frame(self.add_frame, bg=self.bg_color)
                    meal_header.pack(fill="x", padx=20, pady=(10, 0), anchor="w")

                    text, img_path = meal_config.get(meal_type_id, ("Приём пищи", "img/systemIcon/cheatmeal.png"))
                    
                    self.meal_imgs[m_name] = self.load_resized_avatar(img_path, (40, 40))

                    tk.Label(meal_header, image=self.meal_imgs[m_name], text=f" {m_name}:",
                             compound="left", anchor="w", bg=self.bg_color,
                             font=self.get_safe_font(self.fonts, size=12, weight="bold"),
                             padx=5).pack(side="left")

                    current_meal_id = meal_type_id

                tk.Label(self.add_frame, text=f"  • {prod} ({w}г)", anchor="w",
                         font=self.get_safe_font(self.fonts, size=11), bg=self.bg_color).pack(fill="x", padx=(50, 20))

            # Кнопка подключения плана
            tk.Button(self.add_frame, text="Подключить этот план", command=lambda: self.activate_plan(plan_id), relief="groove",
                      bg="#9ee70c", width=30, font=self.get_safe_font(self.fonts, size=14), bd=0).pack(pady=20)
            
        except Exception as e:
            messagebox.showerror("Ошибка БД", str(e))

        self.show_frame(self.add_frame)

    def activate_plan(self, plan_id):
        """Привязывает пользователя к плану и сбрасывает счётчик дней"""
        try:
            conn = get_connection()
            cur = conn.cursor()
            # Если связь уже была - обновляем, если нет - создаём
            cur.execute("""
                INSERT INTO User_Plans (user_id, plan_id, start_date, current_day_index)
                VALUES (%s, %s, CURRENT_DATE, 1)
                ON CONFLICT (user_id) DO UPDATE 
                SET plan_id = %s, start_date = CURRENT_DATE, current_day_index = 1
            """, (self.current_user_id, plan_id, plan_id))
            conn.commit()
            cur.execute("""
                UPDATE Users 
                SET is_folowing_plan = TRUE 
                WHERE user_id = %s 
            """, (self.current_user_id,))
            conn.commit()
            cur.close()
            conn.close()
            
            messagebox.showinfo("Успех", "План питания подключен! Теперь дневник будет сравниваться с его нормами.")
            self.setup_main_screen()
            self.show_frame(self.main_frame)
            
            # Здесь можно обновить лейблы режима или статистику
        except Exception as e:
            messagebox.showerror("Ошибка БД", str(e))

    def sync_plan_day_with_date(self):
        """Автоматически сдвигает день плана при смене даты в календаре"""
        if not self.current_user_id: return
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("SELECT start_date FROM User_Plans WHERE user_id = %s", (self.current_user_id,))
            row = cur.fetchone()
            
            if row:
                start_date = row[0]
                # Считаем разницу в днях и приводим к циклу 1..7
                days_diff = (self.current_day - start_date).days
                new_day_index = (days_diff % 7) + 1
                
                cur.execute("UPDATE User_Plans SET current_day_index = %s WHERE user_id = %s",
                            (new_day_index, self.current_user_id))
                conn.commit()
                
            cur.close()
            conn.close()
        except Exception:
            pass  # Тихо игнорируем, если план ещё не подключён


    def refresh_all_meals(self):
        for meal_type_id, tree in self.meal_tables.items():
            self.load_daily_log(meal_type_id, tree)

    def load_daily_log(self, meal_type_id, tree):
        for row in tree.get_children():
            tree.delete(row)
            
        try:
            conn = get_connection()
            cur = conn.cursor()
            
            cur.execute("""
                SELECT mi.item_id, mi.product_id, p.name, mi.weight_grams, 
                       mi.calories, mi.proteins, mi.fats, mi.carbs
                FROM Meal_items mi
                JOIN Products p ON mi.product_id = p.product_id
                JOIN Meals m ON mi.meal_id = m.meal_id
                JOIN Daily_logs dl ON m.log_id = dl.log_id
                WHERE dl.user_id = %s 
                  AND dl.log_date = %s 
                  AND m.meal_type_id = %s
                ORDER BY mi.item_id
            """, (self.current_user_id, self.current_day, meal_type_id))
            
            for row in cur.fetchall():
                formatted_row = (                       
                    row[0],                          
                    row[1],                          
                    row[2],                          
                    f"{float(row[3]):.0f}",          
                    f"{float(row[4]):.1f}",         
                    f"{float(row[5]):.1f}",          
                    f"{float(row[6]):.1f}",          
                    f"{float(row[7]):.1f}"                 
                )
                tree.insert("", "end", values=formatted_row)
            cur.close()
            conn.close()
        except Exception as e:
            messagebox.showerror("Ошибка БД", str(e))

    def open_add_product_frame(self, meal_type_id):
        for w in self.add_frame.winfo_children(): w.destroy()
        
        # Запоминаем, к какому приёму пищи сейчас добавляем еду
        self.current_meal_type_id = meal_type_id
        self.setup_add_screen()
        # Переходим на экран добавления
        self.show_frame(self.add_frame)

    def get_or_create_meal(self, log_id, meal_type_id):
        conn = get_connection()
        cur = conn.cursor()
        try:
            # Ищем существующую запись
            cur.execute("SELECT meal_id FROM meals WHERE log_id = %s AND meal_type_id = %s", 
                        (log_id, meal_type_id))
            result = cur.fetchone()
            
            if result:
                return result[0]  # Возвращаем существующий ID
            #print(log_id)
            
            # Если нет - создаём новую запись
            cur.execute("""INSERT INTO meals (log_id, meal_type_id) 
                        VALUES (%s, %s) RETURNING meal_id""", 
                        (log_id, meal_type_id))
            
            conn.commit()
            return cur.fetchone()[0]
        finally:
            cur.close()
            conn.close()



    def apply_plan_to_meal(self, meal_type_id):
        """Добавляет в дневник приём пищи согласно активному плану"""
        conn = get_connection()
        cur = conn.cursor()
    
        try:
        
            cur.execute("SELECT plan_id, current_day_index FROM User_Plans WHERE user_id = %s", (self.current_user_id,))
            plan_row = cur.fetchone()

            if not plan_row:
                messagebox.showinfo("Инфо", "У вас не подключен план питания. Выберите его в меню «Планы».")
                return

            plan_id, day_index = plan_row

            # Берём продукты из расписания плана на этот приём пищи
            cur.execute("""
                SELECT ps.product_id, p.calories_per_100_g, p.proteins_per_100_g, 
                       p.fats_per_100_g, p.carbs_per_100_g, ps.recommended_weight_g
                FROM Plan_Schedule ps
                JOIN Products p ON ps.product_id = p.product_id
                WHERE ps.plan_id = %s AND ps.day_index = %s AND ps.meal_type_id = %s
            """, (plan_id, day_index, meal_type_id))

            planned_items = cur.fetchall()
            if not planned_items:
                messagebox.showinfo("Инфо", f"В плане на этот приём пищи (День {day_index}) нет продуктов.")
                return

            #  Находим или создаём слот приёма пищи на сегодня
                        #  Находим или создаём слот приёма пищи (meal_id точно есть в Meals)
            meal_id = self.get_or_create_meal(self.current_log_id, meal_type_id)


            insert_q = """INSERT INTO meal_items 
                          (meal_id, product_id, weight_grams, calories, proteins, fats, carbs) 
                          VALUES (%s, %s, %s, %s, %s, %s, %s)"""
            
            for pid, c100, p100, f100, carb100, w in planned_items:
                # Явно приводим Decimal к float перед вычислениями
                w = float(w)
                cal = float(c100) * w / 100.0
                prot = float(p100) * w / 100.0
                fat = float(f100) * w / 100.0
                carb = float(carb100) * w / 100.0
                
                cur.execute(insert_q, (meal_id, pid, w, cal, prot, fat, carb))

            conn.commit()
            self.recalculate_daily_totals()
            messagebox.showinfo("Успех", f" Приём пищи по плану (День {day_index}) добавлен в дневник!")
            self.toggle_meal_table(meal_type_id)
        except Exception as e:
                conn.rollback()
                messagebox.showerror("Ошибка БД", str(e))
                print(e)
        finally:
                cur.close()
                conn.close()

    def toggle_meal_table(self, meal_type_id):
        tree = self.meal_tables.get(meal_type_id)
        btn = self.meal_buttons.get(meal_type_id)
        if not tree: return

        # winfo_ismapped() проверяет, виден ли виджет прямо сейчас
        if tree.winfo_ismapped():
            tree.pack_forget()  # Прячем
            if btn: btn.config(text="⭣")
        else:
            tree.pack(fill="x", pady=5)  # Показываем
            self.load_daily_log(meal_type_id, tree)  # Грузим данные из БД
            if btn: btn.config(text="⭡")

        self.cal_total.config(text=f"{self.total_calories:.0f}")
        self.prot_total.config(text=f"{self.total_proteins:.1f}")
        self.fats_total.config(text=f"{self.total_fats:.1f}")
        self.carbs_total.config(text=f"{self.total_carbs:.1f}")


    # ========== ЭКРАН ДОБАВЛЕНИЯ ПРОДУКТА ==========
    def setup_add_screen(self):
        # Заголовок
        tk.Label(self.add_frame, text="Добавить продукт", font=self.get_safe_font(self.fonts, size=14, weight="bold"),
                 bg=self.bg_color).pack(pady=15)
        
        # Поиск
        search_frame = tk.Frame(self.add_frame, bg=self.bg_color)
        search_frame.pack(pady=5)
        tk.Label(search_frame, text="Поиск:", font=self.get_safe_font(self.fonts, size=14),
                 bg=self.bg_color).pack(side="left")
        self.search_var = tk.StringVar()
        self.search_var.trace("w", self.filter_products)
        tk.Entry(search_frame, textvariable=self.search_var, width=30, bg=self.bg_color).pack(side="left", padx=5)

        tk.Button(self.add_frame, text="Добавить свой продукт", font=self.get_safe_font(self.fonts, size=10),
                  bg="#e8f5e9", command=self.show_add_custom_product).pack(anchor="ne", padx=20, pady=5)

        style = ttk.Style()
        style.configure("Treeview.Heading", font=self.get_safe_font(self.fonts, size=10))
        style.configure("mystyle.Treeview", font=self.get_safe_font(self.fonts, size=10))
        
        # Таблица продуктов
        self.prod_tree = ttk.Treeview(self.add_frame, 
                                     columns=("name", "calories"), 
                                     show="headings", height=12)
        self.prod_tree.heading("name", text="Продукт")
        self.prod_tree.heading("calories", text="Ккал/100г")
        self.prod_tree.column("name", width=300)
        self.prod_tree.column("calories", width=100)
        self.prod_tree.pack(pady=5, padx=20, fill="both", expand=True)
        self.prod_tree.bind("<Double-1>", self.on_product_select)  # Двойной клик
        
        # Поле веса
        weight_frame = tk.Frame(self.add_frame, bg=self.bg_color)
        weight_frame.pack(pady=5)
        
        # Кнопки
        btn_frame = tk.Frame(self.add_frame, bg=self.bg_color)
        btn_frame.pack(pady=15)
        tk.Button(btn_frame, text="Выбрать", command=self.add_selected_product, font=self.get_safe_font(self.fonts, size=10),
                 bg="#9ee70c", width=30).pack(side="left", padx=10)
        tk.Button(btn_frame, text="Отмена", command=lambda: self.show_frame(self.main_frame), bg="#ffcccc",
                 width=30, font=self.get_safe_font(self.fonts, size=10)).pack(side="left", padx=10)
        
        # Загружаем список продуктов
        self.load_products_list()
    
    def load_products_list(self, search_term=""):
        """Загрузка списка продуктов из БД"""
        for row in self.prod_tree.get_children():
            self.prod_tree.delete(row)
        
        try:
            conn = get_connection()
            cur = conn.cursor()
            query = "SELECT name, calories_per_100_g FROM products"
            if search_term:
                query += f" WHERE LOWER(name) LIKE LOWER('%{search_term}%')"
            query += " ORDER BY name LIMIT 50"
            
            cur.execute(query)
            for row in cur.fetchall():
                self.prod_tree.insert("", "end", values=row)
            cur.close()
            conn.close()
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось загрузить продукты:\n{e}")
    
    def filter_products(self, *args):
        """Фильтрация при вводе в поиск"""
        self.load_products_list(self.search_var.get())
    
    def on_product_select(self, event):
        """Обработка двойного клика по продукту"""
        #self.add_selected_product()
        self.setup_add_product()
        self.show_frame(self.product_frame)


    def show_add_custom_product(self):
        # Создаём модальное окно поверх основного
        dialog = tk.Toplevel(self.root)
        dialog.title("Новый продукт")
        dialog.geometry("420x480")
        dialog.configure(bg=self.bg_color)
        dialog.transient(self.root)
        dialog.grab_set()  # Блокирует клики по основному окну

        tk.Label(dialog, text="Название продукта:", font=self.get_safe_font(self.fonts, size=12), bg=self.bg_color).pack(anchor="w", padx=20, pady=(15, 2))
        name_var = tk.StringVar()
        tk.Entry(dialog, textvariable=name_var, font=self.get_safe_font(self.fonts, size=12), bg="white").pack(fill="x", padx=20, pady=2)

        tk.Label(dialog, text="Категория:", font=self.get_safe_font(self.fonts, size=12), bg=self.bg_color).pack(anchor="w", padx=20, pady=(10, 2))
        cat_combobox = ttk.Combobox(dialog, state="readonly", font=self.get_safe_font(self.fonts, size=12))
        cat_combobox.pack(fill="x", padx=20, pady=2)

        # Загружаем категории из БД
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("SELECT category_id, name FROM Category ORDER BY name")
            cats = cur.fetchall()
            cur.close()
            conn.close()
            
            cat_combobox["values"] = [c[1] for c in cats]
            cat_ids = {c[1]: c[0] for c in cats}  # Маппинг Название → ID
            if cats: cat_combobox.current(0)       # Выбираем первую по умолчанию
        except Exception as e:
            messagebox.showerror("Ошибка БД", str(e))
            return

        tk.Label(dialog, text="КБЖУ на 100г:", font=self.get_safe_font(self.fonts, size=12, weight="bold"), bg=self.bg_color).pack(anchor="w", padx=20, pady=(15, 5))

        frame_nut = tk.Frame(dialog, bg=self.bg_color)
        frame_nut.pack(fill="x", padx=20, pady=2)

        cal_var = tk.StringVar(value="0")
        tk.Label(frame_nut, text="Ккал:", bg=self.bg_color).pack(side="left", padx=2)
        tk.Entry(frame_nut, textvariable=cal_var, width=6).pack(side="left")

        prot_var = tk.StringVar(value="0")
        tk.Label(frame_nut, text="Белки:", bg=self.bg_color).pack(side="left", padx=(10, 2))
        tk.Entry(frame_nut, textvariable=prot_var, width=6).pack(side="left")

        fat_var = tk.StringVar(value="0")
        tk.Label(frame_nut, text="Жиры:", bg=self.bg_color).pack(side="left", padx=(10, 2))
        tk.Entry(frame_nut, textvariable=fat_var, width=6).pack(side="left")

        carb_var = tk.StringVar(value="0")
        tk.Label(frame_nut, text="Угл:", bg=self.bg_color).pack(side="left", padx=(10, 2))
        tk.Entry(frame_nut, textvariable=carb_var, width=6).pack(side="left")

        def save_new():
            name = name_var.get().strip()
            if not name:
                messagebox.showwarning("Внимание", "Введите название продукта!")
                return
            if not cat_combobox.get():
                messagebox.showwarning("Внимание", "Выберите категорию!")
                return

            try:
                cal, prot, fat, carb = float(cal_var.get()), float(prot_var.get()), float(fat_var.get()), float(carb_var.get())
                if any(v < 0 for v in (cal, prot, fat, carb)):
                    raise ValueError("Отрицательные значения")
            except ValueError:
                messagebox.showwarning("Внимание", "КБЖУ должно быть числом ≥ 0!")
                return

            try:
                conn = get_connection()
                cur = conn.cursor()
                # 1️⃣ Вставляем продукт
                cur.execute("""
                    INSERT INTO Products (name, calories_per_100_g, proteins_per_100_g, fats_per_100_g, carbs_per_100_g)
                    VALUES (%s, %s, %s, %s, %s) RETURNING product_id
                """, (name, cal, prot, fat, carb))
                new_pid = cur.fetchone()[0]

                # 2️⃣ Привязываем к категории
                cur.execute("INSERT INTO Product_categories (product_id, category_id) VALUES (%s, %s)",
                            (new_pid, cat_ids[cat_combobox.get()]))
                conn.commit()
                cur.close()
                conn.close()

                messagebox.showinfo("Успех", f"Продукт «{name}» добавлен в базу!")
                dialog.destroy()
                self.load_products_list()  
            except Exception as e:
                messagebox.showerror("Ошибка БД", str(e))

        btn_frame = tk.Frame(dialog, bg=self.bg_color)
        btn_frame.pack(pady=20)
        tk.Button(btn_frame, text="Сохранить", command=save_new, bg="#9ee70c", width=15, font=self.get_safe_font(self.fonts, size=11)).pack(side="left", padx=10)
        tk.Button(btn_frame, text="Отмена", command=dialog.destroy, bg="#ffcccc", width=15, font=self.get_safe_font(self.fonts, size=11)).pack(side="left", padx=10)

    def setup_add_product(self):
        for widget in self.product_frame.winfo_children():
            widget.destroy()
        
        selected = self.prod_tree.selection()
        if not selected:
            messagebox.showwarning("Внимание", "Выберите продукт из списка!")
            return
        item = self.prod_tree.item(selected[0])
        product_name = item["values"][0]

        tk.Button(self.product_frame, image=self.back_img, command=lambda: self.show_frame(self.add_frame), bg=self.bg_color,
                  relief="flat", bd=0).pack(anchor="nw")

        try:
            conn = get_connection()
            cur = conn.cursor()
                  
            cur.execute("SELECT products.product_id, products.name, category.name, calories_per_100_g," \
            " proteins_per_100_g, fats_per_100_g, carbs_per_100_g" \
            " FROM products INNER JOIN product_categories on " \
            " product_categories.product_id = products.product_id " \
            " INNER JOIN category on " \
            " category.category_id = product_categories.category_id" \
            " WHERE products.name = %s", (product_name,))
            
            rows = cur.fetchall()

            if not rows:
                messagebox.showerror("Ошибка", "Продукт не найден в БД")
                self.setup_main_screen()
                self.show_frame(self.main_frame)
                return 
                
            self.current_product_id = rows[0][0]
            self.current_product_name = rows[0][1]
            self.nut_per_100 = {
                'cal': float(rows[0][3]),
                'prot': float(rows[0][4]),
                'fat': float(rows[0][5]),
                'carb': float(rows[0][6])
            }

            all_cats = [row[2] for row in rows if row[2]]
            # Убираем дубликаты, сохраняя порядок
            self.current_category_str = ", ".join(list(dict.fromkeys(all_cats)))


            cur.close()
            conn.close()


            tk.Label(self.product_frame, text=f"{product_name}", bg=self.bg_color,
                font=self.get_safe_font(self.fonts, size=16, weight="bold")).pack(pady=15)
        
            weight_frame = tk.Frame(self.product_frame, bg=self.bg_color)
            weight_frame.pack(pady=5)
            tk.Label(weight_frame, text="Вес (г):", font=self.get_safe_font(self.fonts, size=14), bg=self.bg_color).pack(side="left")
            self.weight_var = tk.IntVar(value=100)
            tk.Spinbox(weight_frame, from_=0, to=1000, textvariable=self.weight_var,
                    width=5).pack(side="left", padx=5)  
            
            nutrition_frame = tk.Frame(self.product_frame, bg=self.bg_color)
            nutrition_frame.pack(pady=5)

            self.lbl_cal = tk.Label(nutrition_frame, text=f"Калории: {self.nut_per_100['cal']:.1f}", 
                                     font=self.get_safe_font(self.fonts, size=14), bg=self.bg_color)
            self.lbl_cal.pack(side="left", padx=5)

            self.lbl_prot = tk.Label(nutrition_frame, text=f"Белки: {self.nut_per_100['prot']:.1f}",
                                      font=self.get_safe_font(self.fonts, size=14), bg=self.bg_color)
            self.lbl_prot.pack(side="left", padx=5)

            self.lbl_fat = tk.Label(nutrition_frame, text=f"Жиры: {self.nut_per_100['fat']:.1f}",
                                     font=self.get_safe_font(self.fonts, size=14), bg=self.bg_color)
            self.lbl_fat.pack(side="left", padx=5)

            self.lbl_carb = tk.Label(nutrition_frame, text=f"Углеводы: {self.nut_per_100['carb']:.1f}",
                                      font=self.get_safe_font(self.fonts, size=14), bg=self.bg_color)
            self.lbl_carb.pack(side="left", padx=5)

            tk.Label(self.product_frame, text=f"Категории: {self.current_category_str}", bg=self.bg_color,
                     font=self.get_safe_font(self.fonts, size=12), fg="#666").pack(pady=(0, 10))

        except Exception as e:
            messagebox.showerror("Ошибка", f"{e}")      

        

        def update_nutrition(*args):
            try:
                w = self.weight_var.get()
                if w < 0: w = 0
                calories = w * self.nut_per_100['cal'] / 100
                proteins = w * self.nut_per_100['prot'] / 100
                fats = w * self.nut_per_100['fat'] / 100
                carbs = w * self.nut_per_100['carb'] / 100
                # Обновляем текст всех лейблов
                self.lbl_cal.config(text=f"Калории: {calories:.1f}")
                self.lbl_prot.config(text=f"Белки: {proteins:.1f}")
                self.lbl_fat.config(text=f"Жиры: {fats:.1f}")
                self.lbl_carb.config(text=f"Углеводы: {carbs:.1f}")

                
            except Exception:
                pass # Игнорируем ошибки при вводе нечисловых символов

        self.weight_var.trace_add("write", update_nutrition)
        
        update_nutrition()      

        tk.Button(self.product_frame, text="Выбрать", command=self.on_add_product, font=self.get_safe_font(self.fonts, size=12),
                 bg="#9ee70c", width=30).pack(pady=20)

        

        
    def on_add_product(self):
        weight = self.weight_var.get()
        if weight <= 0:
            messagebox.showwarning("Ошибка", "Вес должен быть больше 0!")
            return

        product_data = {
            'product_id': self.current_product_id,
            'name': self.current_product_name,
            'weight': weight,
            'cal': round(weight * self.nut_per_100['cal'] / 100, 1),
            'prot': round(weight * self.nut_per_100['prot'] / 100, 1),
            'fat': round(weight * self.nut_per_100['fat'] / 100, 1),
            'carb': round(weight * self.nut_per_100['carb'] / 100, 1)
        }

        self.selected_products.append(product_data)

        self.total_calories += product_data['cal']
        self.total_proteins += product_data['prot']
        self.total_fats += product_data['fat']
        self.total_carbs += product_data['carb']


        try:
            conn = get_connection()
            cur = conn.cursor()

            cur.execute("UPDATE daily_logs"
            " SET total_calories = %s, total_proteins = %s, total_fats = %s, total_carbs = %s  " \
            " WHERE log_id = %s and user_id = %s", (self.total_calories, self.total_proteins, self.total_fats, self.total_carbs, self.current_log_id, self.current_user_id))

            conn.commit()
            cur.close()
            conn.close()



        except Exception as e:
            messagebox.showerror("Ошибка", f"{e}") 


        self.show_frame(self.add_frame)  


    
    def add_selected_product(self):
        meal_id = self.get_or_create_meal(self.current_log_id, self.current_meal_type_id)
        
        conn = get_connection()
        cur = conn.cursor()

        query = "INSERT INTO meal_items(meal_id, product_id, weight_grams, calories, proteins, fats, carbs) VALUES " \
        "(%s, %s, %s, %s, %s, %s, %s)"

        """Добавление выбранного продукта в дневник"""
        for product in self.selected_products:
            cur.execute(query, (meal_id, product['product_id'], product['weight'], product['cal'], 
                                product['prot'], product['fat'], product['carb'], ))
            
        conn.commit()
        cur.close()
        conn.close()
        
        messagebox.showinfo("Успех", "Добавлено ккал")
        self.selected_products.clear()
        
        # Возврат на главный экран и обновление
        self.show_frame(self.main_frame)
        self.toggle_meal_table(self.current_meal_type_id)
        #self.load_daily_log()

    def setup_product_frame(self, mode="add"):
            for widget in self.product_frame.winfo_children():
                widget.destroy()

            tk.Button(self.product_frame, image=self.back_img, command=lambda: self.show_frame(self.add_frame if mode=="add" else self.main_frame),
                       bg=self.bg_color, relief="flat", bd=0).pack(anchor="nw")
                
            self.app_mode = mode

            if mode == "edit":
                tk.Label(self.product_frame, text="Изменение порции", bg=self.bg_color,
                         font=self.get_safe_font(self.fonts, size=16, weight="bold")).pack(pady=15)
                tk.Label(self.product_frame, text=self.edit_product_name, bg=self.bg_color,
                         font=self.get_safe_font(self.fonts, size=14)).pack()
                
                # Предустанавливаем вес из БД
                self.weight_var = tk.IntVar(value=int(self.edit_weight))
            else:
                tk.Label(self.product_frame, text="Новый продукт", bg=self.bg_color,
                         font=self.get_safe_font(self.fonts, size=14)).pack(pady=15)
                self.weight_var = tk.IntVar(value=100)

            cat_text = getattr(self, 'current_category_str', "Категория не указана")
            tk.Label(self.product_frame, text=f"{cat_text}", bg=self.bg_color,
                     font=self.get_safe_font(self.fonts, size=12), fg="#666").pack(pady=(0, 10))

            # Поле веса
            weight_frame = tk.Frame(self.product_frame, bg=self.bg_color)
            weight_frame.pack(pady=10)
            tk.Label(weight_frame, text="Вес (г):", bg=self.bg_color,
                     font=self.get_safe_font(self.fonts, size=14)).pack(side="left")
            tk.Spinbox(weight_frame, from_=10, to=2000, textvariable=self.weight_var, width=5).pack(side="left", padx=5)

            nutrition_frame = tk.Frame(self.product_frame, bg=self.bg_color)
            nutrition_frame.pack(pady=5)
            self.lbl_cal = tk.Label(nutrition_frame, text="", font=self.get_safe_font(self.fonts, size=14), bg=self.bg_color)
            self.lbl_cal.pack(side="left", padx=5)
            self.lbl_prot = tk.Label(nutrition_frame, text="", font=self.get_safe_font(self.fonts, size=14), bg=self.bg_color)
            self.lbl_prot.pack(side="left", padx=5)
            self.lbl_fat = tk.Label(nutrition_frame, text="", font=self.get_safe_font(self.fonts, size=14), bg=self.bg_color)
            self.lbl_fat.pack(side="left", padx=5)
            self.lbl_carb = tk.Label(nutrition_frame, text="", font=self.get_safe_font(self.fonts, size=14), bg=self.bg_color)
            self.lbl_carb.pack(side="left", padx=5)

            def update_labels(*args):
                try:
                    w = self.weight_var.get()  
                    
                    if mode == "edit":
                        base_cal = self.edit_nut['cal'] / self.edit_weight * 100
                        base_prot = self.edit_nut['prot'] / self.edit_weight * 100
                        base_fat = self.edit_nut['fat'] / self.edit_weight * 100
                        base_carb = self.edit_nut['carb'] / self.edit_weight * 100
                    else:
                        base_cal = self.nut_per_100['cal']
                        base_prot = self.nut_per_100['prot']
                        base_fat = self.nut_per_100['fat']
                        base_carb = self.nut_per_100['carb']
                        
                    self.lbl_cal.config(text=f"Ккал: {w*base_cal/100:.1f}")
                    self.lbl_prot.config(text=f"Белки: {w*base_prot/100:.1f}")
                    self.lbl_fat.config(text=f"Жиры: {w*base_fat/100:.1f}")
                    self.lbl_carb.config(text=f"Угл: {w*base_carb/100:.1f}")
                
                except tk.TclError:
                    pass  

            self.weight_var.trace_add("write", update_labels)
            update_labels()

            # Кнопки
            btn_frame = tk.Frame(self.product_frame, bg=self.bg_color)
            btn_frame.pack(pady=15)
            
            if mode == "edit":
                tk.Button(btn_frame, text="Сохранить", command=self.save_edited_product, bg="#9ee70c", width=20,
                          font=self.get_safe_font(self.fonts, size=10)).pack(side="left", padx=5)
                tk.Button(btn_frame, text="Удалить", command=self.delete_from_product_frame, bg="#ffcccc", width=20,
                          font=self.get_safe_font(self.fonts, size=10)).pack(side="left", padx=5)
            else:
                tk.Button(btn_frame, text="Выбрать", command=self.add_selected_product, bg="#9ee70c", width=20,
                          font=self.get_safe_font(self.fonts, size=10)).pack(side="left", padx=10)
                
            


    def recalculate_daily_totals(self):
                try:
                    conn = get_connection()
                    cur = conn.cursor()
                    cur.execute("""
                        UPDATE Daily_logs dl
                        SET total_calories = COALESCE(sub.cal, 0),
                            total_proteins = COALESCE(sub.prot, 0),
                            total_fats = COALESCE(sub.fat, 0),
                            total_carbs = COALESCE(sub.carb, 0)
                        FROM (
                            SELECT SUM(mi.calories) as cal, SUM(mi.proteins) as prot,
                                SUM(mi.fats) as fat, SUM(mi.carbs) as carb
                            FROM meal_items mi JOIN meals m ON mi.meal_id = m.meal_id
                            WHERE m.log_id = %s
                        ) sub
                        WHERE dl.log_id = %s
                    """, (self.current_log_id, self.current_log_id))
                    conn.commit()
                    
                    # Обновляем переменные Python для интерфейса
                    cur.execute("SELECT total_calories, total_proteins, total_fats, total_carbs FROM Daily_logs WHERE log_id = %s", (self.current_log_id,))
                    t = cur.fetchone()
                    if t:
                        self.total_calories, self.total_proteins, self.total_fats, self.total_carbs = map(float, t)
                        self.update_totals_labels()
                        
                    cur.close()
                    conn.close()
                except Exception as e:
                    messagebox.showerror("Ошибка БД", str(e))

    def update_totals_labels(self):
        if hasattr(self, 'cal_total'):
            self.cal_total.config(text=f"{self.total_calories:.0f} ккал")
            self.prot_total.config(text=f"Белки\n{self.total_proteins:.1f} г")
            self.fats_total.config(text=f"Жиры\n{self.total_fats:.1f} г")
            self.carbs_total.config(text=f"Углеводы\n{self.total_carbs:.1f} г")

    def save_edited_product(self):
        """Сохраняет изменённый вес в БД"""
        w = self.weight_var.get()
        if w <= 0: return messagebox.showwarning("Ошибка", "Вес должен быть > 0")
        
        try:
            conn = get_connection()
            cur = conn.cursor()
            
            # Пересчёт БЖУ для нового веса
            base_cal = self.edit_nut['cal'] / self.edit_weight * 100
            base_prot = self.edit_nut['prot'] / self.edit_weight * 100
            base_fat = self.edit_nut['fat'] / self.edit_weight * 100
            base_carb = self.edit_nut['carb'] / self.edit_weight * 100
            
            cur.execute("""
                UPDATE meal_items 
                SET weight_grams = %s, 
                    calories = %s, proteins = %s, fats = %s, carbs = %s
                WHERE item_id = %s
            """, (w, w*base_cal/100, w*base_prot/100, w*base_fat/100, w*base_carb/100, self.edit_item_id))
            
            conn.commit()
            self.recalculate_daily_totals()
            self.show_frame(self.main_frame)
            self.toggle_meal_table(self.current_editing_meal_type)
            cur.close()
            conn.close()
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))

    def delete_selected_item(self, meal_type_id=None):
        """Удаляет запись из БД и пересчитывает итоги"""
        if not meal_type_id:
            for mid, tree in self.meal_tables.items():
                if tree.winfo_ismapped() and tree.selection():
                    meal_type_id = mid
                    break
        if not meal_type_id: return

        tree = self.meal_tables[meal_type_id]
        sel = tree.selection()
        if not sel: return messagebox.showwarning("Внимание", "Выберите строку для удаления")
        
        item_id = tree.item(sel[0])["values"][0]
        name = tree.item(sel[0])["values"][2]
        
        if not messagebox.askyesno("Подтверждение", f"Удалить '{name}'?"): return

        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("DELETE FROM meal_items WHERE item_id = %s", (item_id,))
            conn.commit()
            self.recalculate_daily_totals()
            tree.delete(sel)
            cur.close()
            conn.close()
        except Exception as e:
            messagebox.showerror("Ошибка БД", str(e))

        self.show_frame(self.main_frame)

    def delete_from_product_frame(self):
        """Удаление из режима редактирования"""
        self.delete_selected_item(self.current_editing_meal_type)

# Запуск приложения
if __name__ == "__main__":
    root = tk.Tk()
    root.minsize(1000, 700)
    app = NutritionApp(root)
    root.mainloop()
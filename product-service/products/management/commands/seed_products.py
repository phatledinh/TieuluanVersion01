"""
Seed 50 products across 10 categories — Chapter 2.3

Usage:
    python manage.py seed_products          # seed
    python manage.py seed_products --clear  # clear then re-seed
"""

from django.core.management.base import BaseCommand
from products.models import Category, Product, Book, Electronics, Fashion


class Command(BaseCommand):
    help = 'Seed 50 products across 10 categories'

    def add_arguments(self, parser):
        parser.add_argument('--clear', action='store_true')

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write(self.style.WARNING('Clearing...'))
            Fashion.objects.all().delete()
            Electronics.objects.all().delete()
            Book.objects.all().delete()
            Product.objects.all().delete()
            Category.objects.all().delete()

        cats = self._seed_categories()
        self._seed_books(cats)
        self._seed_electronics(cats)
        self._seed_fashion(cats)

        self.stdout.write(self.style.SUCCESS(
            f'✓ {Product.objects.count()} products / {Category.objects.count()} categories'
        ))

    def _seed_categories(self):
        data = [
            {'name': 'Sách Giáo Trình', 'description': 'Giáo trình đại học'},
            {'name': 'Tiểu Thuyết', 'description': 'Tiểu thuyết trong và ngoài nước'},
            {'name': 'Sách Tham Khảo', 'description': 'Sách chuyên ngành'},
            {'name': 'Điện Thoại', 'description': 'Smartphone các loại'},
            {'name': 'Laptop', 'description': 'Máy tính xách tay'},
            {'name': 'Điện Lạnh', 'description': 'Tủ lạnh, máy lạnh, điều hòa'},
            {'name': 'Phụ Kiện Điện Tử', 'description': 'Tai nghe, sạc, cáp'},
            {'name': 'Quần Áo Nam', 'description': 'Thời trang nam'},
            {'name': 'Quần Áo Nữ', 'description': 'Thời trang nữ'},
            {'name': 'Giày Dép', 'description': 'Giày thể thao, sneaker'},
        ]
        cats = {}
        for d in data:
            c, cr = Category.objects.get_or_create(name=d['name'], defaults=d)
            cats[c.name] = c
            self.stdout.write(f'  {"+" if cr else "~"} {c.name}')
        return cats

    def _seed_books(self, cats):
        books = [
            {'product': {'name': 'Kiến trúc và Thiết kế Phần mềm', 'description': 'Giáo trình microservices, DDD', 'price': 185000, 'stock': 50}, 'detail': {'author': 'Trần Đình Quế', 'publisher': 'NXB Bách Khoa', 'isbn': '978-604-913-001', 'pages': 320, 'language': 'Vietnamese'}, 'cat': 'Sách Giáo Trình'},
            {'product': {'name': 'Cấu trúc dữ liệu và Giải thuật', 'description': 'Giáo trình CTDL cơ bản đến nâng cao', 'price': 165000, 'stock': 40}, 'detail': {'author': 'Nguyễn Văn A', 'publisher': 'NXB ĐHQG', 'isbn': '978-604-913-002', 'pages': 280, 'language': 'Vietnamese'}, 'cat': 'Sách Giáo Trình'},
            {'product': {'name': 'Lập trình Python', 'description': 'Giáo trình Python từ cơ bản đến ứng dụng', 'price': 195000, 'stock': 35}, 'detail': {'author': 'Phạm Minh B', 'publisher': 'NXB Bách Khoa', 'isbn': '978-604-913-003', 'pages': 350, 'language': 'Vietnamese'}, 'cat': 'Sách Giáo Trình'},
            {'product': {'name': 'Mạng máy tính', 'description': 'Giáo trình mạng máy tính và truyền thông', 'price': 175000, 'stock': 30}, 'detail': {'author': 'Lê Văn C', 'publisher': 'NXB ĐHBK', 'isbn': '978-604-913-004', 'pages': 290, 'language': 'Vietnamese'}, 'cat': 'Sách Giáo Trình'},
            {'product': {'name': 'Cơ sở dữ liệu', 'description': 'Giáo trình CSDL quan hệ và NoSQL', 'price': 155000, 'stock': 45}, 'detail': {'author': 'Hoàng Văn D', 'publisher': 'NXB Giáo Dục', 'isbn': '978-604-913-005', 'pages': 260, 'language': 'Vietnamese'}, 'cat': 'Sách Giáo Trình'},
            {'product': {'name': 'Nhà Giả Kim', 'description': 'Tiểu thuyết nổi tiếng của Paulo Coelho', 'price': 79000, 'stock': 100}, 'detail': {'author': 'Paulo Coelho', 'publisher': 'NXB Hội Nhà Văn', 'isbn': '978-604-077-123', 'pages': 228, 'language': 'Vietnamese'}, 'cat': 'Tiểu Thuyết'},
            {'product': {'name': 'Đắc Nhân Tâm', 'description': 'Nghệ thuật đối nhân xử thế', 'price': 86000, 'stock': 90}, 'detail': {'author': 'Dale Carnegie', 'publisher': 'NXB Tổng Hợp', 'isbn': '978-604-077-124', 'pages': 320, 'language': 'Vietnamese'}, 'cat': 'Tiểu Thuyết'},
            {'product': {'name': 'Tuổi trẻ đáng giá bao nhiêu', 'description': 'Sách truyền cảm hứng', 'price': 70000, 'stock': 80}, 'detail': {'author': 'Rosie Nguyễn', 'publisher': 'NXB Hội Nhà Văn', 'isbn': '978-604-077-125', 'pages': 200, 'language': 'Vietnamese'}, 'cat': 'Tiểu Thuyết'},
            {'product': {'name': 'Clean Architecture', 'description': "A Craftsman's Guide to Software Structure", 'price': 450000, 'stock': 30}, 'detail': {'author': 'Robert C. Martin', 'publisher': 'Prentice Hall', 'isbn': '978-013-449-416-6', 'pages': 432, 'language': 'English'}, 'cat': 'Sách Tham Khảo'},
            {'product': {'name': 'Design Patterns', 'description': 'Elements of Reusable OO Software (GoF)', 'price': 520000, 'stock': 20}, 'detail': {'author': 'Gang of Four', 'publisher': 'Addison-Wesley', 'isbn': '978-020-163-361-0', 'pages': 395, 'language': 'English'}, 'cat': 'Sách Tham Khảo'},
        ]
        self._create(cats, books, 'book')

    def _seed_electronics(self, cats):
        items = [
            {'product': {'name': 'iPhone 15 Pro Max', 'description': 'Apple iPhone 15 Pro Max 256GB', 'price': 34990000, 'stock': 25}, 'detail': {'brand': 'Apple', 'warranty': 12, 'model_number': 'A3104', 'specifications': {'ram': '8GB', 'storage': '256GB'}}, 'cat': 'Điện Thoại'},
            {'product': {'name': 'Samsung Galaxy S24 Ultra', 'description': 'Samsung S24 Ultra 512GB', 'price': 33990000, 'stock': 20}, 'detail': {'brand': 'Samsung', 'warranty': 12, 'model_number': 'SM-S928B', 'specifications': {'ram': '12GB', 'storage': '512GB'}}, 'cat': 'Điện Thoại'},
            {'product': {'name': 'Xiaomi 14', 'description': 'Xiaomi 14 Leica 256GB', 'price': 16990000, 'stock': 30}, 'detail': {'brand': 'Xiaomi', 'warranty': 18, 'model_number': 'MI14', 'specifications': {'ram': '12GB', 'storage': '256GB'}}, 'cat': 'Điện Thoại'},
            {'product': {'name': 'OPPO Find X7 Ultra', 'description': 'OPPO Find X7 Ultra 512GB', 'price': 23990000, 'stock': 15}, 'detail': {'brand': 'OPPO', 'warranty': 12, 'model_number': 'FINDX7U', 'specifications': {'ram': '16GB', 'storage': '512GB'}}, 'cat': 'Điện Thoại'},
            {'product': {'name': 'Vivo V30 Pro', 'description': 'Vivo V30 Pro 256GB', 'price': 12490000, 'stock': 35}, 'detail': {'brand': 'Vivo', 'warranty': 12, 'model_number': 'V30PRO', 'specifications': {'ram': '12GB', 'storage': '256GB'}}, 'cat': 'Điện Thoại'},
            {'product': {'name': 'MacBook Pro 14 M3 Pro', 'description': 'MacBook Pro 14 M3 Pro 18GB/512GB', 'price': 49990000, 'stock': 15}, 'detail': {'brand': 'Apple', 'warranty': 12, 'model_number': 'MRX33', 'specifications': {'ram': '18GB', 'storage': '512GB SSD'}}, 'cat': 'Laptop'},
            {'product': {'name': 'Dell XPS 15', 'description': 'Dell XPS 15 i7/16GB/512GB', 'price': 38990000, 'stock': 12}, 'detail': {'brand': 'Dell', 'warranty': 24, 'model_number': 'XPS9530', 'specifications': {'ram': '16GB', 'storage': '512GB SSD'}}, 'cat': 'Laptop'},
            {'product': {'name': 'ASUS ROG Strix G16', 'description': 'Laptop gaming ASUS ROG i9/32GB', 'price': 42990000, 'stock': 10}, 'detail': {'brand': 'ASUS', 'warranty': 24, 'model_number': 'G614JV', 'specifications': {'ram': '32GB', 'gpu': 'RTX 4060'}}, 'cat': 'Laptop'},
            {'product': {'name': 'Lenovo ThinkPad X1 Carbon', 'description': 'ThinkPad X1 Carbon Gen 11', 'price': 35990000, 'stock': 18}, 'detail': {'brand': 'Lenovo', 'warranty': 36, 'model_number': 'X1C11', 'specifications': {'ram': '16GB', 'storage': '512GB'}}, 'cat': 'Laptop'},
            {'product': {'name': 'HP Pavilion 15', 'description': 'HP Pavilion 15 i5/8GB/512GB', 'price': 15990000, 'stock': 25}, 'detail': {'brand': 'HP', 'warranty': 12, 'model_number': 'PV15-EG', 'specifications': {'ram': '8GB', 'storage': '512GB'}}, 'cat': 'Laptop'},
            {'product': {'name': 'Tủ lạnh Samsung Inverter 360L', 'description': 'Samsung RT35 Inverter 360 lít', 'price': 10490000, 'stock': 10}, 'detail': {'brand': 'Samsung', 'warranty': 24, 'model_number': 'RT35CG', 'specifications': {'capacity': '360L'}}, 'cat': 'Điện Lạnh'},
            {'product': {'name': 'Điều hòa Daikin Inverter 1.5HP', 'description': 'Daikin FTKZ35 Inverter 1.5HP', 'price': 16990000, 'stock': 8}, 'detail': {'brand': 'Daikin', 'warranty': 24, 'model_number': 'FTKZ35', 'specifications': {'capacity': '12000 BTU'}}, 'cat': 'Điện Lạnh'},
            {'product': {'name': 'Máy giặt LG Inverter 10kg', 'description': 'LG T2310VSAM Inverter 10kg', 'price': 8990000, 'stock': 12}, 'detail': {'brand': 'LG', 'warranty': 24, 'model_number': 'T2310', 'specifications': {'capacity': '10kg'}}, 'cat': 'Điện Lạnh'},
            {'product': {'name': 'Tủ lạnh Panasonic 380L', 'description': 'Panasonic NR-BX421 Inverter 380L', 'price': 12490000, 'stock': 8}, 'detail': {'brand': 'Panasonic', 'warranty': 24, 'model_number': 'NR-BX421', 'specifications': {'capacity': '380L'}}, 'cat': 'Điện Lạnh'},
            {'product': {'name': 'Điều hòa Panasonic 1HP', 'description': 'Panasonic CU/CS-N9WKH Inverter 1HP', 'price': 8990000, 'stock': 15}, 'detail': {'brand': 'Panasonic', 'warranty': 24, 'model_number': 'N9WKH', 'specifications': {'capacity': '9000 BTU'}}, 'cat': 'Điện Lạnh'},
            {'product': {'name': 'Tai nghe Sony WH-1000XM5', 'description': 'Sony WH-1000XM5 chống ồn', 'price': 8490000, 'stock': 20}, 'detail': {'brand': 'Sony', 'warranty': 12, 'model_number': 'WH1000XM5', 'specifications': {'type': 'Over-ear', 'anc': True}}, 'cat': 'Phụ Kiện Điện Tử'},
            {'product': {'name': 'Apple AirPods Pro 2', 'description': 'AirPods Pro thế hệ 2 USB-C', 'price': 6790000, 'stock': 25}, 'detail': {'brand': 'Apple', 'warranty': 12, 'model_number': 'MTJV3', 'specifications': {'type': 'In-ear', 'anc': True}}, 'cat': 'Phụ Kiện Điện Tử'},
            {'product': {'name': 'Sạc nhanh Anker 65W', 'description': 'Anker Nano II 65W USB-C GaN', 'price': 890000, 'stock': 50}, 'detail': {'brand': 'Anker', 'warranty': 18, 'model_number': 'A2663', 'specifications': {'power': '65W', 'ports': 1}}, 'cat': 'Phụ Kiện Điện Tử'},
            {'product': {'name': 'Chuột Logitech MX Master 3S', 'description': 'Chuột không dây Logitech MX Master', 'price': 2490000, 'stock': 30}, 'detail': {'brand': 'Logitech', 'warranty': 24, 'model_number': 'MXM3S', 'specifications': {'dpi': 8000, 'type': 'Wireless'}}, 'cat': 'Phụ Kiện Điện Tử'},
            {'product': {'name': 'Bàn phím cơ Keychron K8', 'description': 'Keychron K8 Pro TKL Wireless', 'price': 2290000, 'stock': 20}, 'detail': {'brand': 'Keychron', 'warranty': 12, 'model_number': 'K8PRO', 'specifications': {'layout': 'TKL', 'switch': 'Gateron Brown'}}, 'cat': 'Phụ Kiện Điện Tử'},
        ]
        self._create(cats, items, 'electronics')

    def _seed_fashion(self, cats):
        items = [
            {'product': {'name': 'Áo Polo Nam Classic', 'description': 'Áo polo nam cotton cao cấp', 'price': 350000, 'stock': 80}, 'detail': {'size': 'L', 'color': 'Navy Blue', 'material': 'Cotton 100%', 'gender': 'M'}, 'cat': 'Quần Áo Nam'},
            {'product': {'name': 'Quần Jeans Slim Fit', 'description': 'Quần jeans nam slim fit co giãn', 'price': 490000, 'stock': 60}, 'detail': {'size': '32', 'color': 'Dark Blue', 'material': 'Denim 98%', 'gender': 'M'}, 'cat': 'Quần Áo Nam'},
            {'product': {'name': 'Áo Thun Nam Basic', 'description': 'Áo thun nam cổ tròn basic', 'price': 199000, 'stock': 100}, 'detail': {'size': 'M', 'color': 'White', 'material': 'Cotton', 'gender': 'M'}, 'cat': 'Quần Áo Nam'},
            {'product': {'name': 'Áo Sơ Mi Nam Oxford', 'description': 'Áo sơ mi nam Oxford dài tay', 'price': 420000, 'stock': 45}, 'detail': {'size': 'L', 'color': 'Light Blue', 'material': 'Oxford Cotton', 'gender': 'M'}, 'cat': 'Quần Áo Nam'},
            {'product': {'name': 'Quần Kaki Nam', 'description': 'Quần kaki nam regular fit', 'price': 380000, 'stock': 55}, 'detail': {'size': '31', 'color': 'Beige', 'material': 'Cotton Kaki', 'gender': 'M'}, 'cat': 'Quần Áo Nam'},
            {'product': {'name': 'Áo Khoác Hoodie Nữ', 'description': 'Hoodie nữ oversize nỉ bông', 'price': 280000, 'stock': 70}, 'detail': {'size': 'M', 'color': 'Pastel Pink', 'material': 'Nỉ bông', 'gender': 'F'}, 'cat': 'Quần Áo Nữ'},
            {'product': {'name': 'Đầm Midi Nữ', 'description': 'Đầm midi dự tiệc thanh lịch', 'price': 550000, 'stock': 30}, 'detail': {'size': 'S', 'color': 'Black', 'material': 'Polyester', 'gender': 'F'}, 'cat': 'Quần Áo Nữ'},
            {'product': {'name': 'Áo Blouse Nữ', 'description': 'Áo blouse nữ công sở', 'price': 320000, 'stock': 40}, 'detail': {'size': 'M', 'color': 'White', 'material': 'Lụa satin', 'gender': 'F'}, 'cat': 'Quần Áo Nữ'},
            {'product': {'name': 'Chân Váy A Nữ', 'description': 'Chân váy chữ A dáng xòe', 'price': 290000, 'stock': 50}, 'detail': {'size': 'S', 'color': 'Cream', 'material': 'Tuyết mưa', 'gender': 'F'}, 'cat': 'Quần Áo Nữ'},
            {'product': {'name': 'Quần Jeans Nữ Skinny', 'description': 'Quần jeans nữ skinny co giãn', 'price': 450000, 'stock': 40}, 'detail': {'size': '27', 'color': 'Blue', 'material': 'Denim Stretch', 'gender': 'F'}, 'cat': 'Quần Áo Nữ'},
            {'product': {'name': 'Giày Nike Air Max 90', 'description': 'Nike Air Max 90 chính hãng', 'price': 3290000, 'stock': 35}, 'detail': {'size': '42', 'color': 'White/Black', 'material': 'Leather+Mesh', 'gender': 'U'}, 'cat': 'Giày Dép'},
            {'product': {'name': 'Giày Adidas Ultraboost', 'description': 'Adidas Ultraboost Light', 'price': 4500000, 'stock': 25}, 'detail': {'size': '41', 'color': 'Core Black', 'material': 'Primeknit', 'gender': 'U'}, 'cat': 'Giày Dép'},
            {'product': {'name': 'Dép Birkenstock Arizona', 'description': 'Birkenstock Arizona Classic', 'price': 2190000, 'stock': 20}, 'detail': {'size': '40', 'color': 'Brown', 'material': 'Da bò', 'gender': 'U'}, 'cat': 'Giày Dép'},
            {'product': {'name': 'Giày New Balance 574', 'description': 'NB 574 Classic Lifestyle', 'price': 2690000, 'stock': 30}, 'detail': {'size': '42', 'color': 'Grey/Navy', 'material': 'Suede+Mesh', 'gender': 'U'}, 'cat': 'Giày Dép'},
            {'product': {'name': 'Giày Converse Chuck 70', 'description': 'Converse Chuck 70 High Top', 'price': 1890000, 'stock': 40}, 'detail': {'size': '41', 'color': 'Black', 'material': 'Canvas', 'gender': 'U'}, 'cat': 'Giày Dép'},
        ]
        self._create(cats, items, 'fashion')

    def _create(self, cats, items, domain):
        model_map = {'book': Book, 'electronics': Electronics, 'fashion': Fashion}
        detail_model = model_map[domain]
        for item in items:
            pd = item['product'].copy()
            pd['category'] = cats[item['cat']]
            product, created = Product.objects.get_or_create(name=pd['name'], defaults=pd)
            if created:
                detail_model.objects.create(product=product, **item['detail'])
                self.stdout.write(f'  + {product.name}')
            else:
                self.stdout.write(f'  ~ {product.name} (exists)')

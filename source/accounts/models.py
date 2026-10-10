import io
import os
from PIL import Image

from django.conf import settings
from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class Profile(models.Model):
    """Mở rộng thông tin người dùng: ảnh đại diện và tùy chọn cá nhân."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    avatar = models.ImageField(upload_to="avatars/%Y/%m/", blank=True, null=True)

    class Meta:
        verbose_name = "Hồ sơ cá nhân"
        verbose_name_plural = "Hồ sơ cá nhân"

    def __str__(self):
        return f"Hồ sơ của {self.user.username}"

    def save(self, *args, **kwargs):
        # Tự động nén và resize ảnh avatar về tối đa 300x300 pixel, định dạng WebP
        # giúp dung lượng nhỏ gọn (~15-30KB) và tải cực nhanh trên web/mobile.
        if self.avatar and hasattr(self.avatar, "file"):
            try:
                # Kiểm tra nếu đây là file mới được upload
                if not self.avatar._committed:
                    im = Image.open(self.avatar).convert("RGB")
                    # Crop vuông từ tâm (center crop)
                    w, h = im.size
                    min_dim = min(w, h)
                    left = (w - min_dim) // 2
                    top = (h - min_dim) // 2
                    im_cropped = im.crop((left, top, left + min_dim, top + min_dim))
                    # Resize về chuẩn 300x300
                    im_resized = im_cropped.resize((300, 300), Image.Resampling.LANCZOS)
                    # Nén WebP chất lượng 85%
                    out_io = io.BytesIO()
                    im_resized.save(out_io, format="WEBP", quality=85)
                    # Đổi tên file sang .webp
                    base_name, _ = os.path.splitext(os.path.basename(self.avatar.name))
                    new_filename = f"{base_name}.webp"
                    self.avatar.save(new_filename, ContentFile(out_io.getvalue()), save=False)
            except Exception:
                pass
        super().save(*args, **kwargs)

    def xoa_file_avatar(self):
        """Xóa file ảnh vật lý trên ổ đĩa để tránh lãng phí dung lượng hosting."""
        if self.avatar:
            try:
                path = self.avatar.path
                if os.path.isfile(path):
                    os.remove(path)
            except Exception:
                pass
            self.avatar = None


@receiver(post_save, sender=User)
def tao_hoac_luu_profile(sender, instance, created, **kwargs):
    """Tự động tạo Profile khi User mới được đăng ký."""
    if created:
        Profile.objects.create(user=instance)

import html
import logging
import threading
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

logger = logging.getLogger(__name__)


def _send_feedback_email_task(feedback_data):
    """后台子线程执行发送邮件任务"""
    try:
        from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None)
        raw_recipients = getattr(settings, "FEEDBACK_NOTIFY_EMAIL", None) or from_email
        if not raw_recipients:
            logger.warning("[FeedbackEmail] 未配置发件人或收件人邮箱，跳过发送反馈通知邮件")
            return

        # 支持逗号分隔的多个收件人
        if isinstance(raw_recipients, str):
            recipient_list = [r.strip() for r in raw_recipients.split(",") if r.strip()]
        elif isinstance(raw_recipients, (list, tuple)):
            recipient_list = list(raw_recipients)
        else:
            recipient_list = [str(raw_recipients)]

        if not recipient_list:
            logger.warning("[FeedbackEmail] 收件人列表为空，跳过发送反馈通知邮件")
            return

        feedback_id = feedback_data.get("id")
        channel = feedback_data.get("channel") or "未记录"
        device_id = feedback_data.get("device_id") or "未记录"
        fb_type = feedback_data.get("fb_type") or feedback_data.get("type") or "未分类"
        content = feedback_data.get("content") or ""
        contact = feedback_data.get("contact") or "未填写"
        created_at = feedback_data.get("created_at")

        if isinstance(created_at, str):
            created_at_str = created_at
        elif created_at:
            created_at_str = timezone.localtime(created_at).strftime("%Y-%m-%d %H:%M:%S")
        else:
            created_at_str = timezone.localtime().strftime("%Y-%m-%d %H:%M:%S")

        # 整理附件图片完整地址
        nginx_media_url = getattr(settings, "NGINX_MEDIA_URL", "").rstrip("/")
        images = feedback_data.get("images") or []
        if isinstance(images, str):
            images = [images]

        image_urls = []
        for img in images:
            if not img:
                continue
            if img.startswith(("http://", "https://")):
                image_urls.append(img)
            else:
                image_urls.append(f"{nginx_media_url}/{img.lstrip('/')}")

        # 邮件标题
        subject = f"【本我壁纸】收到新的用户反馈 [{channel}] - {fb_type}"

        # 纯文本正文（兼容不支持 HTML 的客户端）
        text_lines = [
            "【本我壁纸】收到新的用户反馈通知",
            "=" * 36,
            f"反馈ID: {feedback_id}",
            f"设备ID: {device_id}",
            f"来 源: {channel}",
            f"类 型: {fb_type}",
            f"联 系: {contact}",
            f"时 间: {created_at_str}",
            "",
            "反馈内容:",
            content,
            "",
        ]
        if image_urls:
            text_lines.append(f"附带图片 ({len(image_urls)} 张):")
            for idx, u in enumerate(image_urls, start=1):
                text_lines.append(f"  [{idx}] {u}")
        text_message = "\n".join(text_lines)

        # HTML 富文本正文
        escaped_content = html.escape(content).replace("\n", "<br/>")
        escaped_contact = html.escape(contact)
        escaped_channel = html.escape(channel)
        escaped_device_id = html.escape(device_id)
        escaped_type = html.escape(fb_type)

        images_html = ""
        if image_urls:
            img_cards = []
            for u in image_urls:
                img_cards.append(
                    f'<a href="{u}" target="_blank" style="display:inline-block;margin:6px 6px 0 0;text-decoration:none;">'
                    f'<img src="{u}" alt="反馈图片" style="max-height:160px;max-width:220px;border-radius:6px;border:1px solid #e2e8f0;object-fit:cover;vertical-align:top;" />'
                    f'</a>'
                )
            images_html = f"""
            <div style="margin-top:16px;">
                <div style="font-weight:600;font-size:14px;color:#334155;margin-bottom:8px;">附带图片 ({len(image_urls)}张，点击可查看原图)：</div>
                <div style="display:flex;flex-wrap:wrap;">{''.join(img_cards)}</div>
            </div>
            """

        html_message = f"""
        <!DOCTYPE html>
        <html>
        <head><meta charset="utf-8"></head>
        <body style="margin:0;padding:24px;background-color:#f1f5f9;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;color:#1e293b;">
            <div style="max-width:620px;margin:0 auto;background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 4px 16px rgba(0,0,0,0.06);border:1px solid #e2e8f0;">
                <div style="background:linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);padding:20px 24px;color:#ffffff;">
                    <div style="font-size:13px;letter-spacing:1px;opacity:0.85;text-transform:uppercase;">Ego Wallpapers · 用户反馈</div>
                    <div style="font-size:20px;font-weight:700;margin-top:4px;">收到新的用户反馈</div>
                </div>
                <div style="padding:24px;">
                    <table style="width:100%;border-collapse:collapse;margin-bottom:16px;font-size:14px;">
                        <tr>
                            <td style="padding:6px 0;width:80px;color:#64748b;font-weight:500;">渠道来源</td>
                            <td style="padding:6px 0;color:#0f172a;"><span style="background:#e0f2fe;color:#0284c7;padding:3px 8px;border-radius:4px;font-size:12px;font-weight:600;">{escaped_channel}</span></td>
                        </tr>
                        <tr>
                            <td style="padding:6px 0;color:#64748b;font-weight:500;">设备 ID</td>
                            <td style="padding:6px 0;color:#475569;font-family:monospace;font-size:12px;">{escaped_device_id}</td>
                        </tr>
                        <tr>
                            <td style="padding:6px 0;color:#64748b;font-weight:500;">反馈类型</td>
                            <td style="padding:6px 0;color:#0f172a;"><span style="background:#fef3c7;color:#d97706;padding:3px 8px;border-radius:4px;font-size:12px;font-weight:600;">{escaped_type}</span></td>
                        </tr>
                        <tr>
                            <td style="padding:6px 0;color:#64748b;font-weight:500;">联系方式</td>
                            <td style="padding:6px 0;color:#0f172a;">{escaped_contact}</td>
                        </tr>
                        <tr>
                            <td style="padding:6px 0;color:#64748b;font-weight:500;">提交时间</td>
                            <td style="padding:6px 0;color:#64748b;font-size:13px;">{created_at_str}</td>
                        </tr>
                    </table>

                    <div style="background:#f8fafc;border-left:4px solid #3b82f6;padding:14px 16px;border-radius:0 8px 8px 0;margin-top:12px;">
                        <div style="font-weight:600;font-size:13px;color:#475569;margin-bottom:6px;">反馈详情</div>
                        <div style="font-size:14px;line-height:1.7;color:#1e293b;word-break:break-word;">{escaped_content}</div>
                    </div>

                    {images_html}

                    <div style="margin-top:28px;padding-top:16px;border-top:1px dashed #e2e8f0;font-size:12px;color:#94a3b8;text-align:center;">
                        此邮件为本我壁纸后台自动发出，反馈 ID: #{feedback_id}
                    </div>
                </div>
            </div>
        </body>
        </html>
        """

        send_mail(
            subject=subject,
            message=text_message,
            from_email=from_email,
            recipient_list=recipient_list,
            html_message=html_message,
            fail_silently=False,
        )
        logger.info(f"[FeedbackEmail] 用户反馈通知邮件已成功发送至 {recipient_list} (feedback_id={feedback_id})")
    except Exception as e:
        logger.error(f"[FeedbackEmail] 发送用户反馈邮件通知异常: {e}", exc_info=True)


def send_feedback_notification_async(feedback):
    """
    非阻塞异步发送用户反馈邮件通知
    :param feedback: Feedback 实例或相关字典
    """
    if not feedback:
        return

    data = {
        "id": getattr(feedback, "id", None),
        "channel": getattr(feedback, "channel", None),
        "device_id": getattr(feedback, "device_id", None),
        "fb_type": getattr(feedback, "fb_type", None) or getattr(feedback, "type", None),
        "content": getattr(feedback, "content", None),
        "contact": getattr(feedback, "contact", None),
        "images": getattr(feedback, "images", None),
        "created_at": getattr(feedback, "created_at", None),
    }

    t = threading.Thread(target=_send_feedback_email_task, args=(data,), daemon=True)
    t.start()

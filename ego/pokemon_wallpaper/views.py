from django.shortcuts import render, redirect
from django.http import HttpResponse

from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required


def login_view(request):
    login_redirect_url = "pokemon_wallpaper:index"
    next_url = request.GET.get('next', login_redirect_url)

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            # 重定向到 next 参数或默认页面
            return redirect(request.POST.get('next', login_redirect_url))
        else:
            return render(request, 'pokemon_wallpaper/login.html', {
                'error': '用户名或密码错误',
                'next': next_url  # 保持 next 参数传递
            })

    # GET 请求时传递 next 参数到模板
    return render(request, 'pokemon_wallpaper/login.html', {'next': next_url})


def logout_view(request):
    logout(request)
    return redirect('pokemon_wallpaper:login')


@login_required
def index(request):
    context = {"latest_question_list": 3}
    return render(request, "pokemon_wallpaper/index.html", context)

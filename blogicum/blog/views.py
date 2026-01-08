from django.contrib.auth import login
from django.shortcuts import get_object_or_404, render, redirect
from django.utils import timezone
from django.http import HttpResponseForbidden
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.forms import UserChangeForm
from django.core.paginator import Paginator
from django.db.models import Count
from .models import Post, Category, Comment
from .forms import PostForm, CommentForm


def index(request):
    post_list = Post.objects.select_related(
        'category', 'location', 'author'
    ).filter(
        pub_date__lte=timezone.now(),
        is_published=True,
        category__is_published=True
    ).order_by('-pub_date')[:5]

    # Добавляем пагинацию (задание 3)
    paginator = Paginator(post_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Добавляем количество комментариев (задание 7)
    post_list = post_list.annotate(comment_count=Count('comments'))
    
    context = {'page_obj': page_obj}
    return render(request, 'blog/index.html', context)


def post_detail(request, post_id):
    post = get_object_or_404(
        Post.objects.select_related('category', 'location', 'author'),
        pk=post_id,
        pub_date__lte=timezone.now(),
        is_published=True,
        category__is_published=True
    )
    
    # Добавляем комментарии и форму (задание 7)
    comments = post.comments.all()
    if request.method == 'POST' and request.user.is_authenticated:
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.post = post
            comment.author = request.user
            comment.save()
            return redirect('blog:post_detail', post_id=post_id)
    else:
        form = CommentForm()
    
    context = {
        'post': post,
        'comments': comments,
        'form': form
    }
    return render(request, 'blog/detail.html', context)


def category_posts(request, category_slug):
    category = get_object_or_404(
        Category,
        slug=category_slug,
        is_published=True
    )

    post_list = Post.objects.select_related(
        'category', 'location', 'author'
    ).filter(
        category=category,
        pub_date__lte=timezone.now(),
        is_published=True
    ).order_by('-pub_date')
    
    # Добавляем пагинацию (задание 3)
    paginator = Paginator(post_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Добавляем количество комментариев (задание 7)
    post_list = post_list.annotate(comment_count=Count('comments'))

    context = {
        'category': category,
        'page_obj': page_obj
    }
    return render(request, 'blog/category.html', context)


# 2.2 Регистрация пользователя
def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('blog:index')  
    else:
        form = UserCreationForm()
    return render(request, 'registration/registration_form.html', {'form': form})


# 2.3 Страница профиля пользователя
def profile(request, username):
    user = get_object_or_404(User, username=username)
    
    # Базовый QuerySet для постов пользователя
    post_list = Post.objects.filter(author=user)
    
    # Если пользователь не владелец профиля, показываем только опубликованные посты
    if request.user != user:
        post_list = post_list.filter(
            pub_date__lte=timezone.now(),
            is_published=True,
            category__is_published=True
        )
    
    # Аннотация комментариев ДО пагинации
    post_list = post_list.annotate(comment_count=Count('comments'))
    
    # Пагинация
    paginator = Paginator(post_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'profile': user,
        'page_obj': page_obj,
    }
    return render(request, 'blog/profile.html', context)


# 2.4 Редактирование профиля
@login_required
def edit_profile(request):
    from django.contrib.auth.forms import UserChangeForm
    
    if request.method == 'POST':
        form = UserChangeForm(request.POST, instance=request.user)
        # Ограничиваем поля только нужными
        allowed_fields = ['username', 'first_name', 'last_name', 'email']
        for field_name in list(form.fields.keys()):
            if field_name not in allowed_fields:
                form.fields.pop(field_name, None)
        
        if form.is_valid():
            form.save()
            return redirect('blog:profile', username=request.user.username)
    else:
        form = UserChangeForm(instance=request.user)
        # Ограничиваем поля только нужными
        allowed_fields = ['username', 'first_name', 'last_name', 'email']
        for field_name in list(form.fields.keys()):
            if field_name not in allowed_fields:
                form.fields.pop(field_name, None)
    
    return render(request, 'blog/user.html', {'form': form})


# 5. Создание поста
@login_required
def create_post(request):
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            return redirect('blog:profile', username=request.user.username)
    else:
        form = PostForm()
    return render(request, 'blog/create.html', {'form': form})


# 6. Редактирование поста
@login_required
def edit_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    
    # Проверяем, что пользователь - автор поста
    if post.author != request.user:
        return HttpResponseForbidden("Вы не можете редактировать этот пост")
    
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            form.save()
            return redirect('blog:detail', post_id=post_id)
    else:
        form = PostForm(instance=post)
    
    return render(request, 'blog/create.html', {'form': form, 'post': post})


# 7.1 Добавление комментария
@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    if request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.post = post
            comment.author = request.user
            comment.save()
    return redirect('blog:post_detail', post_id=post_id)


# 7.2 Редактирование комментария
@login_required
def edit_comment(request, post_id, comment_id):
    comment = get_object_or_404(Comment, id=comment_id, post_id=post_id)
    
    # Проверяем, что пользователь - автор комментария
    if comment.author != request.user:
        return HttpResponseForbidden("Вы не можете редактировать этот комментарий")
    
    if request.method == 'POST':
        form = CommentForm(request.POST, instance=comment)
        if form.is_valid():
            form.save()
            return redirect('blog:post_detail', post_id=post_id)
    else:
        form = CommentForm(instance=comment)
    
    return render(request, 'blog/comment.html', {'form': form, 'comment': comment})


# 8.1 Удаление поста
@login_required
def delete_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    
    if post.author != request.user:
        return HttpResponseForbidden("Вы не можете удалить этот пост")
    
    if request.method == 'POST':
        post.delete()
        return redirect('blog:profile', username=request.user.username)
    
    return render(request, 'blog/detail.html', {'post': post})


# 8.2 Удаление комментария
@login_required
def delete_comment(request, post_id, comment_id):
    comment = get_object_or_404(Comment, id=comment_id, post_id=post_id)
    
    if comment.author != request.user:
        return HttpResponseForbidden("Вы не можете удалить этот комментарий")
    
    if request.method == 'POST':
        comment.delete()
    
    return redirect('blog:post_detail', post_id=post_id)

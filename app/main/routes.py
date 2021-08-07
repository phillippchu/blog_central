from datetime import datetime
from flask import render_template, flash, redirect, url_for, request, abort, current_app
from flask_login import current_user, login_required
from app import db
from app.main import main
from app.main.forms import EditProfileForm, EmptyForm, PostForm, UpdatePostForm
from app.models import User, Post


@main.before_request
def before_request():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.utcnow()
        db.session.commit()


@main.route("/blog_central")
def blog_central():
    return render_template("blog_central.html")


@main.route("/", methods=["GET", "POST"])
@main.route("/index", methods=["GET", "POST"])
@login_required
def index():
    form = PostForm()
    if form.validate_on_submit():
        post = Post(body=form.post.data, author=current_user)
        db.session.add(post)
        db.session.commit()
        flash("Your post is now live!", "success")
        return redirect(url_for("main.index"))
    page = request.args.get("page", 1, type=int)
    posts = current_user.followed_posts().paginate(
        page, current_app.config["POSTS_PER_PAGE"], False)
    next_url = url_for(
        "main.index", page=posts.next_num) if posts.has_next else None
    prev_url = url_for(
        "main.index", page=posts.prev_num) if posts.has_prev else None
    return render_template("index.html", form=form, posts=posts.items, next_url=next_url, prev_url=prev_url)


@main.route("/explore")
@login_required
def explore():
    page = request.args.get("page", 1, type=int)
    posts = Post.query.order_by(Post.timestamp.desc()).paginate(
        page, current_app.config["POSTS_PER_PAGE"], False)
    next_url = url_for(
        "main.explore", page=posts.next_num) if posts.has_next else None
    prev_url = url_for(
        "main.explore", page=posts.prev_num) if posts.has_prev else None
    return render_template("explore.html", posts=posts.items, next_url=next_url, prev_url=prev_url)


@main.route("/user/<username>", methods=["GET", "POST"])
@login_required
def user(username):
    user = User.query.filter_by(username=username).first_or_404()
    page = request.args.get("page", 1, type=int)
    posts = user.posts.order_by(Post.timestamp.desc()).paginate(
        page, current_app.config["POSTS_PER_PAGE"], False)
    next_url = url_for("main.user", username=user.username,
                       page=posts.next_num) if posts.has_next else None
    prev_url = url_for("main.user", username=user.username,
                       page=posts.prev_num) if posts.has_prev else None
    form = EmptyForm()
    return render_template("user.html", user=user, posts=posts.items, next_url=next_url, prev_url=prev_url, form=form)


@main.route("/user/<string:username>/edit_profile", methods=["GET", "POST"])
@login_required
def edit_profile(username):
    form = EditProfileForm(current_user.username)
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.about_me = form.about_me.data
        db.session.commit()
        flash("Your changes have been saved.", "success")
        return redirect(url_for("main.user", username=current_user.username))
    elif request.method == "GET":
        form.username.data = current_user.username
        form.about_me.data = current_user.about_me
    page = request.args.get("page", 1, type=int)
    user = User.query.filter_by(username=username).first_or_404()
    posts = user.posts.order_by(Post.timestamp.desc()).paginate(
        page, current_app.config["POSTS_PER_PAGE"], False)
    next_url = url_for("main.edit_profile", username=user.username,
                       page=posts.next_num) if posts.has_next else None
    prev_url = url_for("main.edit_profile", username=user.username,
                       page=posts.prev_num) if posts.has_prev else None
    if user != current_user:
        abort(403)
    return render_template("edit_profile.html", user=user, posts=posts.items, next_url=next_url, prev_url=prev_url, form=form)


@main.route("/follow/<username>", methods=["POST"])
@login_required
def follow(username):
    form = EmptyForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=username).first()
        if user is None:
            flash("User {} not found.".format(username), "danger")
            return redirect(url_for("main.index"))
        if user == current_user:
            flash("You cannot follow yourself!", "warning")
            return redirect(url_for("main.user", username=username))
        current_user.follow(user)
        db.session.commit()
        flash("You are following {}!".format(username), "success")
        return redirect(url_for("main.user", username=username))
    else:
        return redirect(url_for("main.index"))


@main.route("/unfollow/<username>", methods=["POST"])
@login_required
def unfollow(username):
    form = EmptyForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=username).first()
        if user is None:
            flash("User {} not found.".format(username), "danger")
            return redirect(url_for("main.index"))
        if user == current_user:
            flash("You cannot unfollow yourself!", "warning")
            return redirect(url_for("main.user", username=username))
        current_user.unfollow(user)
        db.session.commit()
        flash("You unfollowed {}".format(username), "success")
        return redirect(url_for("main.user", username=username))
    else:
        return redirect(url_for("main.index"))


@main.route("/add_post", methods=["GET", "POST"])
@login_required
def add_post():
    form = PostForm()
    if form.validate_on_submit():
        post = Post(body=form.post.data, author=current_user)
        db.session.add(post)
        db.session.commit()
        flash("Your post is now live!", "success")
        return redirect(url_for("main.index"))
    return render_template("add_post.html", form=form)


@main.route("/post/<int:post_id>/update_post", methods=["GET", "POST"])
@login_required
def update_post(post_id):
    post_to_update = Post.query.get_or_404(post_id)
    if post_to_update.author != current_user:
        abort(403)
    form = UpdatePostForm()
    if form.validate_on_submit():
        post_to_update.body = form.post.data
        db.session.commit()
        flash("Your post has been updated!", "success")
        return redirect(url_for("main.user", username=current_user.username))
    elif request.method == "GET":
        form.post.data = post_to_update.body
    return render_template("update_post.html", form=form, legend="Update Post")


@main.route("/post/<int:post_id>/delete_post", methods=["GET", "POST"])
@login_required
def delete_post(post_id):
    post_to_delete = Post.query.get_or_404(post_id)
    if post_to_delete.author != current_user:
        abort(403)
    db.session.delete(post_to_delete)
    db.session.commit()
    flash("Your post has been deleted!", "success")
    return redirect(url_for("main.user", username=current_user.username))


@main.route("/like/<int:post_id>/<action>")
@login_required
def like_action(post_id, action):
    post = Post.query.filter_by(id=post_id).first_or_404()
    if action == "like":
        current_user.like_post(post)
        db.session.commit()
    if action == "unlike":
        current_user.unlike_post(post)
        db.session.commit()
    return redirect(request.referrer)

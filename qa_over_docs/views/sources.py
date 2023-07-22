from flask import request, redirect, flash
from werkzeug.utils import secure_filename
import os, shutil, validators
from qa_over_docs import vector_db
from qa_over_docs import app, context, ALLOWED_EXTENSIONS, UPLOAD_FOLDER, CONTEXT_FILE, SOURCES_FILE


@app.route('/create_collection')
def create_collection():
    if not vector_db.collection_exists():
        vector_db.create_collections()
    context["collection_exists"] = True
    flash("Collection successfully created", "success")
    return redirect("/")


def allowed_file(filename):
    return '.' in filename and \
            filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/include_source", methods=['GET', 'POST'])
def include_source():
    if request.method == 'POST':
        file = request.files['file']
        # If the user does not select a file, the browser submits an
        # empty file without a filename.
        if file.filename == '':
            context["sources_to_add"].append(request.form["include-url"])
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(path)

            context["sources_to_add"].append(filename)

    return redirect("/")


@app.route("/clear_sources_to_add")
def clear_sources_to_add():
    context["sources_to_add"] = []
    shutil.rmtree(UPLOAD_FOLDER)
    os.mkdir(UPLOAD_FOLDER)
    return redirect("/")


@app.route("/add_sources", methods=['GET', 'POST'])
def add_sources():
    if request.method == 'POST':
        if context["sources_to_add"]:
            valid_sources = []
            
            for source in context["sources_to_add"]:
                if validators.url(source) or os.path.exists(os.path.join(UPLOAD_FOLDER, source)):
                    valid_sources.append(source)
            if valid_sources:
                vector_db.add_sources(valid_sources)
                context["sources"].extend(valid_sources)
                clear_sources_to_add()
                flash("Successfully added sources", "success")
            else:
                flash("No valid sources provided", "warning")
        else:
            flash("No sources to add", "warning")
    return redirect("/")


@app.route("/remove_source/<int:index>")
def remove_source(index: int):
    source = context["sources"][index]
    vector_db.remove_source(source)
    flash(f"Successfully removed {source}", "primary")
    context["sources"].pop(index)
    return redirect("/")


@app.route("/delete_collection")
def delete_collection():
    vector_db.delete_collection()

    if os.path.exists(CONTEXT_FILE):
        os.remove(CONTEXT_FILE)
    if os.path.exists(SOURCES_FILE):
        os.remove(SOURCES_FILE)

    context["collection_exists"] = False
    context["sources"] = []
    context["response_time"] = None
    context["chat_items"] = []

    flash("Collection successfully deleted", "primary")
    return redirect("/")
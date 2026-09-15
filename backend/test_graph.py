from graph import app

result = app.invoke({
    "user_id": "bed90765-40a9-4020-9baa-49ff17fce7d8",
    "matches": [],
    "results": [],
    "digest_text": ""
})

print(result["digest_text"])
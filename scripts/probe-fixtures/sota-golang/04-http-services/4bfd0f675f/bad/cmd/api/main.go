package main

func main() {
	log.Fatal(http.ListenAndServe(":8080", routes()))
}

ZIPS := all_calls.zip \
				call_foreign.zip \
				conses.zip \
				mapping.zip \
				series_concurrent.zip

all: $(ZIPS)

%.zip: %.py
	../../bin/c9c $^ $@

clean:
	-rm $(ZIPS)

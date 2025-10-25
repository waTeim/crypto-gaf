             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
[<class 'decimal.DivisionUndefined'>]
  File "/app/app.py", line 117, in getOrderbookField
    samples[i].append((askPriceSamples[i][j]*askSizeSamples[i][j] - bidPriceSamples[i][j]*bidSizeSamples[i][j])/(askSizeSamples[i][j] + bidSizeSamples[i][j]))
                      ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
decimal.InvalidOperation: [<class 'decimal.DivisionUndefined'>]
Traceback (most recent call last):
  File "/app/app.py", line 212, in main
    orderbookField = future_orderbook.result()
                     ^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.11/concurrent/futures/_base.py", line 449, in result

